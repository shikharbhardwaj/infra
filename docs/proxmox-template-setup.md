## Proxmox VM template setup

### Setup requirements

* SSH key
* democratic-csi pre requisites
    * `sudo apt-get install -y cifs-utils nfs-utils`
    * ```
        # Install the following system packages
        sudo apt-get install -y open-iscsi lsscsi sg3-utils multipath-tools scsitools

        # Enable multipathing
        sudo tee /etc/multipath.conf <<-'EOF'
        defaults {
            user_friendly_names yes
            find_multipaths yes
        }
        EOF

        sudo systemctl enable multipath-tools.service
        sudo service multipath-tools restart

        # Ensure that open-iscsi and multipath-tools are enabled and running
        sudo systemctl status multipath-tools
        sudo systemctl enable open-iscsi.service
        sudo service open-iscsi start
        sudo systemctl status open-iscsi
        ```
* https://tailscale.com/kb/1293/cloud-init

### Setup steps

Taken from: https://github.com/UntouchedWagons/Ubuntu-CloudInit-Docs

#### Prerequisites (for each node):
1. Save the SSH public keys you need the VMs to be setup with at `~/authorized_keys`.
2. Save the vendor.yaml file below at `/var/lib/vz/snippets/vendor.yaml`

`vendor.yaml`

```yaml
#cloud-config

package_update: true
package_upgrade: true

packages:
  - qemu-guest-agent
  - vim-tiny
  - cifs-utils
  - nfs-common
  - open-iscsi
  - lsscsi
  - sg3-utils
  - multipath-tools
  - scsitools

runcmd:
    # democratic-csi setup
    - |
      sudo tee /etc/multipath.conf <<-'EOF'
       defaults {
            user_friendly_names yes
            find_multipaths yes
        }
      EOF
    - sudo systemctl enable multipath-tools.service
    - sudo service multipath-tools restart
    - sudo systemctl status multipath-tools
    - sudo systemctl enable open-iscsi.service
    - sudo service open-iscsi start
    - sudo systemctl status open-iscsi
    # Tailscale setup
    - ['sh', '-c', 'curl -fsSL https://tailscale.com/install.sh | sh']
    - ['sh', '-c', "echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf && echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf && sudo sysctl -p /etc/sysctl.d/99-tailscale.conf" ]
    - ['tailscale', 'up', '--auth-key=<AUTH_KEY>']
    # Qemu guest agent
    - systemctl start qemu-guest-agent
    - reboot
# Taken from https://forum.proxmox.com/threads/combining-custom-cloud-init-with-auto-generated.59008/page-3#post-428772
```

#### Template creation

1. Download the image

    ```
    > wget -q https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
    > qemu-img resize noble-server-cloudimg-amd64.img 32G
    ```

2. Setup the VM
    ```
    #sudo qm create 8001 --name "ubuntu-2404-cloudinit-template" --ostype l26 \
        --memory 2048 \
        --agent 1 \
        --bios ovmf --machine q35 --efidisk0 local-lvm:0,pre-enrolled-keys=0 \
        --cpu host --socket 1 --cores 2 \
        --vga serial0 --serial0 socket  \
        --net0 virtio,bridge=vmbr0
    ```

3.  Configure VM hardware
    ```
    sudo qm importdisk 8001 noble-server-cloudimg-amd64.img local-lvm
    sudo qm set 8001 --scsihw virtio-scsi-pci --virtio0 local-lvm:vm-8001-disk-1,discard=on
    sudo qm set 8001 --boot order=virtio0
    sudo qm set 8001 --scsi1 local-lvm:cloudinit
    ```

4. Configure cloud-init settings
    ```
    export CLEARTEXT_PASSWORD="<your vm template password>"
    sudo qm set 8001 --cicustom "vendor=local:snippets/vendor.yaml"
    sudo qm set 8001 --tags ubuntu-template,24.04,cloudinit
    sudo qm set 8001 --ciuser <your username>
    sudo qm set 8001 --cipassword $(openssl passwd -6 $CLEARTEXT_PASSWORD)
    sudo qm set 8001 --sshkeys ~/authorized_keys
    sudo qm set 8001 --ipconfig0 ip=dhcp
    ```

5. Convert the VM to a template

    ```
    sudo qm template 8001
    ```


### Creating the Kubernetes node VMs

1. Clone the VM template, update the hardware (CPU/RAM).
2. Start the VM, then go to the Omada dashboard and setup a DHCP IP reservation for the node.
3. Restart the VM.
4. Install k3s as a control plane node.

    ```
    # On existing control plane node.
    sudo cat /var/lib/rancher/k3s/server/node-token

    # On the new VM
    export SECRET=<node-token-obtained-above>
    curl -sfL https://get.k3s.io | K3S_URL=https://<EXISTING_NODE_IP>:6443 INSTALL_K3S_CHANNEL=v1.30.9+k3s1 K3S_TOKEN=$SECRET sh -s - server
    ```
