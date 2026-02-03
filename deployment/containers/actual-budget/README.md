# Actual Budget

Actual Budget is a local-first personal finance tool based on zero-based budgeting. It's a privacy-focused budgeting app that syncs across devices.

## Container Details

- **Image**: `actualbudget/actual-server:latest`
- **Port**: 5006
- **Data Volume**: `~/containers/actual-budget/data` mounted to `/data`

## Deployment

The container is configured to run via Podman Quadlet and systemd.

### Installation

To install this container on a host, add `actual-budget` to the inventory file for the desired host:

```yaml
your-hostname:
  - actual-budget
```

Then run:

```bash
./install --inventory inventory.yml
```

Or to install on all hosts:

```bash
./install --all
```

### Manual Management

Enable and start the service:

```bash
systemctl --user enable --now actual-budget
```

Check status:

```bash
systemctl --user status actual-budget
```

View logs:

```bash
journalctl --user -u actual-budget -f
```

## Access

Once deployed, Actual Budget will be available at:

- Direct access: `http://<host-ip>:5006`
- Via Traefik: `https://budget.{{ oci_host }}`

## Features

- Zero-based budgeting methodology
- Bank sync (optional)
- End-to-end encryption
- Multi-device sync
- Import from other budgeting tools
- Local-first architecture

## Documentation

- Official docs: https://actualbudget.org/docs/
- GitHub: https://github.com/actualbudget/actual
- Community: https://discord.gg/actualbudget
