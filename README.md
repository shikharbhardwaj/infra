# notthebee/infra

An Ansible playbook that sets up an Ubuntu-based home media server/NAS with reasonable security, auto-updates, e-mail notifications for S.M.A.R.T./Snapraid errors and remote access via Tailscale VPN. 

It assumes a fresh Ubuntu Server 20.04 install, access to a non-root user with sudo privileges and a public SSH key. This can be configured during the installation process.

The playbook is mostly being developed for personal use, so stuff is going to be constantly changing and breaking. Use at your own risk and don't expect any help in setting it up on your machine.

![Example screenshot](https://user-images.githubusercontent.com/8502456/188171845-e2ba5680-e1e6-4308-b84a-0a6cb9191cd2.png)

## Kudos

* This started as a fork of [notthebee/infra](https://github.com/notthebee/infra), after watching this [YouTube video](https://www.youtube.com/watch?v=f5jNJDaztqk).

## Apps

The repo has a bunch of apps left over from the fork, only the ones listed below are working in this setup.

#### Services
* [Homer](https://hub.docker.com/r/b4bz/homer) (A static home page)
* [Vaultwarden](https://hub.docker.com/r/vaultwarden/server) (A FOSS Bitwarden fork written in Rust)
* [Tailscale](https://hub.docker.com/r/linuxserver/wireguard) (A wireguard based VPN service)
* [Etherpad](https://github.com/ether/etherpad-lite) (A collaborative text editor)
* [code-server](https://github.com/coder/code-server) (VSCode in the browser)
* [Gitea](https://github.com/go-gitea/gitea) (Self-hosted git service)
* [Minio](https://github.com/minio/minio) (S3-like object storage)
* [Seafile](https://github.com/haiwen/seafile) (File sync and sharing)
* [quotes-api](https://github.com/shikharbhardwaj/quotes-api) (Self-hosted API to get random quotes from random places)

#### System
* [PiKVM](https://github.com/pikvm/pikvm) (Raspberry Pi based IP-KVM for remote access)
* [netdata](https://github.com/netdata/netdata) (Real-time performance monitoring)
* [Authelia](https://hub.docker.com/r/authelia/authelia) (An authentication provider)
* [scrutiny](https://github.com/AnalogJ/scrutiny) (SMART monioring web UI)

#### Misc
* [Watchtower](https://hub.docker.com/r/containrrr/watchtower) (An automated updater for Docker images)
* [traefik](https://github.com/traefik/traefik) (Application proxy forwarding requests to hosted apps)

## Other features:
* MergerFS with Snapraid
* Fail2Ban for Vaultwarden
* CrowdSec with the iptables bouncer

## Usage
Install Ansible (macOS):
```
brew install ansible
```

Clone the repository:
```
git clone https://github.com/notthebee/infra
```

Create a host varialbe file and adjust the variables:
```
cd infra/ansible
mkdir -p host_vars/YOUR_HOSTNAME
vi host_vars/YOUR_HOSTNAME/vars.yml
```

Create a Keychain item for your Ansible Vault password (on macOS):
```
security add-generic-password \
               -a YOUR_USERNAME \
               -s ansible-vault-password \
               -w
```

The `pass.sh` script will extract the Ansible Vault password from your Keychain automatically each time Ansible requests it.

Create an encrypted `secret.yml` file and adjust the variables:
```
ansible-vault create host_vars/YOUR_HOSTNAME/secret.yml
ansible-vault edit host_vars/YOUR_HOSTNAME/secret.yml
```

Add your custom inventory file to `hosts`:
```
cp hosts_example hosts
vi hosts
```

Install the dependencies:
```
ansible-galaxy install -r requirements.yml
```

Finally, run the playbook:
```
ansible-playbook run.yml -l your-host-here -K
```
The "-K" parameter is only necessary for the first run, since the playbook configures passwordless sudo for the main login user

For consecutive runs, if you only want to update the Docker containers, you can run the playbook like this:
```
ansible-playbook run.yml --tags="port,containers"
```


