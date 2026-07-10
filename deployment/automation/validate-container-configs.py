#!/usr/bin/env python3
"""Validates podman quadlet container definitions under deployment/containers/.

Checks:
  - Each *.container file has the required systemd unit sections and an Image=.
  - Every {{ var }} placeholder used in a container's files is declared in
    deployment/containers/secrets.example.yml.
  - Every Secret=<name>,... reference in a .container file is declared in that
    container's config.yml under podman_secrets, and vice versa.
  - Every container listed for a host in inventory.yml/inventory.example.yml
    has a matching directory under deployment/containers/.
"""
import os
import re
import sys

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONTAINERS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "containers")

REQUIRED_SECTIONS = ["[Unit]", "[Container]", "[Service]", "[Install]"]
PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")
SECRET_RE = re.compile(r"^Secret=([^,\s]+)")

errors = []


def load_known_secrets():
    path = os.path.join(CONTAINERS_DIR, "secrets.example.yml")
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return set(data.keys())


def check_placeholders(path, text, known_secrets):
    undeclared = set(PLACEHOLDER_RE.findall(text)) - known_secrets
    if undeclared:
        errors.append(
            f"{path}: uses {{{{ var }}}} placeholder(s) not declared in "
            f"secrets.example.yml: {', '.join(sorted(undeclared))}"
        )


def check_container_file(path, known_secrets):
    with open(path) as f:
        content = f.read()

    for section in REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"{path}: missing required section {section}")

    if "Image=" not in content:
        errors.append(f"{path}: missing Image= directive")

    check_placeholders(path, content, known_secrets)

    return {
        SECRET_RE.match(line.strip()).group(1)
        for line in content.splitlines()
        if SECRET_RE.match(line.strip())
    }


def check_config_yml(container_dir, secret_refs, known_secrets):
    config_path = os.path.join(container_dir, "config.yml")
    declared = set()
    if os.path.exists(config_path):
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        declared = set(data.get("podman_secrets", []) or [])

    missing_in_config = secret_refs - declared
    if missing_in_config:
        errors.append(
            f"{container_dir}: Secret= directive(s) not declared in config.yml "
            f"podman_secrets: {', '.join(sorted(missing_in_config))}"
        )

    extra_in_config = declared - secret_refs
    if extra_in_config:
        errors.append(
            f"{container_dir}: config.yml podman_secrets not referenced by any "
            f"Secret= directive: {', '.join(sorted(extra_in_config))}"
        )

    undeclared_in_example = declared - known_secrets
    if undeclared_in_example:
        errors.append(
            f"{container_dir}: podman_secrets not present in secrets.example.yml: "
            f"{', '.join(sorted(undeclared_in_example))}"
        )


def check_inventory_references(known_containers):
    for name in ("inventory.yml", "inventory.example.yml"):
        path = os.path.join(CONTAINERS_DIR, name)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            continue
        for host, containers in data.items():
            for container in containers or []:
                if container not in known_containers:
                    errors.append(
                        f"{path}: host '{host}' lists container '{container}' "
                        f"with no matching directory under deployment/containers/"
                    )


def main():
    known_secrets = load_known_secrets()
    known_containers = set()

    for entry in sorted(os.listdir(CONTAINERS_DIR)):
        container_dir = os.path.join(CONTAINERS_DIR, entry)
        if not os.path.isdir(container_dir):
            continue
        known_containers.add(entry)

        container_files = [
            f for f in os.listdir(container_dir) if f.endswith(".container")
        ]
        for cf in container_files:
            path = os.path.join(container_dir, cf)
            secret_refs = check_container_file(path, known_secrets)
            check_config_yml(container_dir, secret_refs, known_secrets)

        # Check placeholders in any other text files in the directory (e.g.
        # traefik.yml, dynamic.yml, acquis.yaml).
        for root, _, files in os.walk(container_dir):
            for fname in files:
                if fname.endswith(".container") or fname == "config.yml":
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        text = f.read()
                except (UnicodeDecodeError, IsADirectoryError):
                    continue
                check_placeholders(fpath, text, known_secrets)

    check_inventory_references(known_containers)

    if errors:
        print("Container config validation failed:\n")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("All container configs valid.")


if __name__ == "__main__":
    main()
