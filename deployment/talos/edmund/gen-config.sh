#!/usr/bin/env bash
# Render edmund's Talos machine config + talosconfig into out/ (gitignored).
#
# Required env:
#   NODE_LAN_IP   edmund's reserved LAN IP on saras's network (DHCP reservation)
#   LAN_SUBNET    that LAN's CIDR - pins kubelet/etcd to it so they never pick
#                 the tailscale interface
#   TS_AUTHKEY    tailscale auth key (only needed for the first apply; state
#                 persists in /var/lib/tailscale after that)
#
# out/secrets.yaml is the cluster's root of trust (CAs, tokens, etcd keys). It
# is generated once and reused on every later render; losing it means
# rebuilding the cluster. The durable copy is secrets.vault.yaml (ansible-vault
# encrypted, committed - too big for a Bitwarden note), restored from here.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
: "${NODE_LAN_IP:?}" "${LAN_SUBNET:?}" "${TS_AUTHKEY:?}"

mkdir -p out
if [[ ! -f out/secrets.yaml ]]; then
    if [[ -f secrets.vault.yaml ]]; then
        # Never mint a new bundle for a cluster that already exists - the
        # node would reject every config and talosconfig rendered from it.
        ansible-vault decrypt --vault-password-file ../../../pass.sh \
            --output out/secrets.yaml secrets.vault.yaml
        chmod 600 out/secrets.yaml
    else
        talosctl gen secrets -o out/secrets.yaml
        echo "New cluster secrets generated - encrypt and commit them:" >&2
        echo "  ansible-vault encrypt --vault-password-file ../../../pass.sh --output secrets.vault.yaml out/secrets.yaml" >&2
    fi
fi

# Host-specific values that can't live in git (LAN addressing, auth key).
cat > out/node.yaml <<EOF
machine:
  # Talos API cert: reachable as edmund over the tailnet, or the LAN IP
  # during bootstrap.
  certSANs: [edmund, ${NODE_LAN_IP}]
cluster:
  etcd:
    advertisedSubnets: [${LAN_SUBNET}]
---
apiVersion: v1alpha1
kind: KubeNodeConfig
nodeIP:
  validSubnets: [${LAN_SUBNET}]
---
apiVersion: v1alpha1
kind: ExtensionServiceConfig
name: tailscale
environment:
  - TS_AUTHKEY=${TS_AUTHKEY}
  - TS_HOSTNAME=edmund
  # Re-login only if not already logged in - a reboot after the auth key
  # expires must not knock the node off the tailnet.
  - TS_AUTH_ONCE=true
EOF

# The in-cluster endpoint is the LAN IP: the node itself has no MagicDNS, so
# it can't resolve "edmund". Clients use the tailnet name instead (below) -
# Talos already adds the node's hostname and every address (tailnet IP
# included) to the kube-apiserver cert.
#
# The talosconfig (admin client cert) is only minted when missing: a fresh
# cert's notBefore is "now" by this machine's clock, so if it runs even a
# second ahead of the node the cert is briefly rejected as not-yet-valid.
# (With a single output type, talosctl treats --output as a file, not a dir.)
if [[ -f out/talosconfig ]]; then
    output_args=(--output-types controlplane --output out/controlplane.yaml)
else
    output_args=(--output-types controlplane,talosconfig --output out/)
fi

talosctl gen config edmund "https://${NODE_LAN_IP}:6443" \
    --with-secrets out/secrets.yaml \
    --config-patch @patches/install.yaml \
    --config-patch @patches/single-node.yaml \
    --config-patch @patches/iscsi.yaml \
    --config-patch @out/node.yaml \
    "${output_args[@]}" --force

talosctl --talosconfig out/talosconfig config endpoint edmund
talosctl --talosconfig out/talosconfig config node edmund
