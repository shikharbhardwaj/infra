update-ubuntu-hosts:
	ansible-playbook -i hosts playbooks/update-ubuntu-hosts.yml

update-proxmox-hosts:
	ansible-playbook -i hosts playbooks/update-proxmox-hosts.yml

configure-node-exporter:
	ansible-playbook -i hosts playbooks/configure-node-exporter.yml
