# TrueNAS monitoring — saras VM

Fleet monitoring for the **TrueNAS VM running on the saras Proxmox host**. This
is the appliance guest that has the LSI **SAS2308 HBA PCIe-passed-through**, so
drive temps and the HBA temp are collected *inside* it and shipped to the fleet
observability stack on tyr (VictoriaMetrics + vmagent + Grafana).

Like `deployment/mac/`, this is **applied by hand**, not by the tyr/gliese
`install` mechanism — TrueNAS is an appliance and only takes apps through its
own UI.

## What it deploys

A single **Custom App** (`compose.yaml`) with two services and one scrape target
(`:9100`, labelled `host=truenas-saras`):

| Service | Role |
| --- | --- |
| `node-exporter` | Host networking, so it's reachable at the VM's tailnet IP; reads host CPU/mem/net/fs/ZFS from bind-mounted `/proc`,`/sys`,`/` (via `--path.*`); serves the textfile metrics on `:9100`. |
| `metrics-collector` | Privileged sidecar; runs the HBA tool + `smartctl` and writes `hba_temperature_celsius` and `disk_temperature_celsius` into the shared textfile volume that node-exporter serves. |

**No Tailscale sidecar or auth key.** This VM's Tailscale runs with host
networking, so the tailnet interface is in the host network namespace;
`network_mode: host` is enough for node-exporter to answer at the VM's tailnet
IP. (node-exporter reads host CPU/mem/fs from the bind mounts + `--path.*`, so
those stay correct regardless of networking.)

## One-time setup on the saras TrueNAS VM

1. **Stage the collector script on a pool** (same pool as the HBA tool,
   `/mnt/main/apps`):
   ```
   /mnt/main/apps/hba-temp/sas2308_temp                    # already present
   /mnt/main/apps/truenas-monitoring/collector-loop.sh     # copy this file here
   ```
   Ownership/mode don't matter much: the `metrics-collector` container runs as
   **root** and TrueNAS's Docker does no userns remapping, so container-root =
   host uid 0 and reads the file regardless. `chmod 644` is fine (it's run as
   `bash /collector-loop.sh`, so no execute bit is needed). If your pool isn't
   `main`, adjust the `/mnt/main/...` paths in `compose.yaml`.

2. **Install the Custom App**: Apps → Discover Apps → Custom App → install from
   YAML, paste `compose.yaml`. No environment variables to set.

3. **Wire the scrape target**: note the VM's existing tailnet IP (`tailscale ip
   -4` on the VM) and put it into tyr's local
   `~/infra/deployment/containers/secrets.yml` as:
   ```yaml
   truenas_saras_tailscale_ip: "100.x.y.z"
   ```
   (already declared in `secrets.example.yml`). vmagent's `truenas-saras` job
   picks it up on the next container deploy on tyr.

## Verify

```bash
# On the TrueNAS VM: is the exporter answering with the custom temps?
curl -s http://127.0.0.1:9100/metrics | grep -E 'hba_temperature_celsius|disk_temperature_celsius'

# On tyr: is vmagent scraping the target?
curl -s http://127.0.0.1:8429/targets | grep truenas-saras

# In VictoriaMetrics (from tyr): normalized series present?
#   node:hba_temperature:celsius{host="truenas-saras"}
#   node:disk_temperature:celsius{host="truenas-saras"}
```

The **TrueNAS Overview** Grafana dashboard
(`deployment/containers/grafana/provisioning/dashboards/json/truenas-overview.json`)
plots drive temps, HBA temp, pool/dataset capacity, CPU/mem/net and ZFS ARC,
with a `$node` picker scoped to TrueNAS hosts.

## Notes & gotchas

- The HBA tool runs as **root** in the collector container, so no `sudo` — the
  interactive form is `sudo /mnt/main/apps/hba-temp/sas2308_temp /dev/mpt2ctl`.
  If `sas2308_temp`'s output format isn't a bare number, adjust the parse in
  `collector-loop.sh` (`first_number` grabs the first number it sees).
- `network_mode: host` means node-exporter also listens on the VM's LAN IP at
  `:9100` (unauthenticated, like every other node_exporter in the fleet). Make
  sure nothing else on the VM already binds `:9100`.
- Sleeping disks are skipped each cycle (`smartctl -n standby`), so a spun-down
  drive shows a gap rather than waking on every poll.
- `smartmontools` is `apt install`ed on container start (adds a little startup
  latency and a network dependency); bake a small image later if that matters.
- **Onboarding the thor TrueNAS VM**: copy this directory to
  `deployment/truenas/thor/`, add a `truenas-thor` scrape job in
  `deployment/containers/vmagent/scrape.yml` (mirroring `truenas-saras`),
  declare `truenas_thor_tailscale_ip`, and install the same app on it.
