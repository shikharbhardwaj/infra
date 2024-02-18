## Proxmox setup breadcrumbs

Documenting the steps taken to setup Proxmox on Phoenix (HP Pavilion 15 laptop).

### Installation

1. Grab the ISO from the [proxmox website](https://www.proxmox.com/en/downloads/category/iso-images-pve) and make a bootable USB.
2. Mostly follow on screen instructions, in addition to:
    1. Connect to a wired (ethernet) network and grab an IP.
    2. Set that IP as reserved for this machine in your network switch configuration.

### Post-install

1. Disable suspend on lid close.

```
# Edit /etc/systemd/logind.conf to set the following.
HandleLidSwitch=ignore
```

2. Setup package sources and updates.

```
echo "deb http://download.proxmox.com/debian/pve bullseye pve-no-subscription" >> /etc/apt/sources.list

# Comment out the entry in /etc/apt/sources.list.d/pve-enterprise.list
```

3. <details>
    <summary>Enable IOMMU and load vfio kernel modules.</summary>

    1. Update `/etc/default/grub` to add `intel_iommu=on` option to `GRUB_CMDLINE_LINUX_DEFAULT`.
    2. Run `update-grub` and reboot.
    3. Check if IOMMU groups show up using `find /sys | grep dmar`.
    4. Add vfio kernel modules to `/etc/modules`
        ```
        vfio
        vfio_iommu_type1
        vfio_pci
        vfio_virqfd
        ```
    </details>
4. Make default bridge VLAN aware using the Proxmox UI.

5.  <details>
    <summary>Setup WiFi</summary>

    ```
    apt-get install network-manager
    # Update /etc/NetworkManager/NetworkManager.conf manage wifi networks.
    nmcli d wifi list
    nmcli d wifi connect 
    ```
    </details>

6. Use `ssh-copy-id` to setup your SSH public key as `authorized_keys` in the Proxmox node.

7. Install tailscale and make one of the nodes a subnet router.

### Setting up VMs

1. Create a base tempalate with Ubuntu server ISO for the VMs using the Ansible playbook in `proxmox-k8s-cluster/create-ubuntu-template`.

