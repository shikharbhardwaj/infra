update-ubuntu-hosts:
	ansible-playbook -i hosts playbooks/update-ubuntu-hosts.yml

update-proxmox-hosts:
	ansible-playbook -i hosts playbooks/update-proxmox-hosts.yml

configure-netdata-streaming:
	ansible-playbook -i hosts playbooks/configure-netdata-streaming.yml
