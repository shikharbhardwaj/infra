# Crafty Controller

This directory contains the configuration for running Crafty Controller in a container using Podman.

## What is Crafty Controller?

Crafty Controller is a web-based management panel for Minecraft servers. It allows you to:

- Manage multiple Minecraft servers from a single web interface
- Monitor server performance and resource usage
- Schedule automated backups and restarts
- Manage server files and configurations
- Control user access with role-based permissions

## Configuration

The setup includes the following files:

- `crafty.container`: Podman quadlet file that defines the container configuration
- `config.yml`: Configuration file for the installation script

## Ports

The following ports are exposed:

- `8000`: Web interface (HTTP)
- `8443`: Web interface (HTTPS)
- `25565`: Default Minecraft server port

## Volumes

The following volumes are mounted for persistent data:

- `/crafty/data`: Crafty Controller data
- `/crafty/servers`: Minecraft server files
- `/crafty/backups`: Server backups
- `/crafty/logs`: Log files

## Installation

To install and run Crafty Controller:

```bash
cd /path/to/infra
./deployment/containers/install
```

## Access

Once installed, Crafty Controller will be available at:

- `https://crafty.yourdomain.com` (if configured with Traefik)
- `http://your-server-ip:8000` (direct access)

## Initial Setup

On first access, you'll need to create an admin account. Follow the on-screen instructions to complete the setup.

## Documentation

For more information, visit the [Crafty Controller documentation](https://docs.craftycontrol.com/).
