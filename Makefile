update-ubuntu-hosts:
	ansible-playbook -i hosts playbooks/update-ubuntu-hosts.yml

update-proxmox-hosts:
	ansible-playbook -i hosts playbooks/update-proxmox-hosts.yml

configure-node-exporter:
	ansible-playbook -i hosts playbooks/configure-node-exporter.yml

# Needs the ansible vault (pass.sh -> Bitwarden) and a machine on saras's LAN.
bootstrap-edmund:
	ansible-playbook -i hosts --vault-password-file pass.sh playbooks/bootstrap-edmund.yml
