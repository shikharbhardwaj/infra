#!/bin/bash

# If ANSIBLE_PASSWORD is not set, get it from bitwarden.
if [ -z "$ANSIBLE_PASSWORD" ]; then
    bw get password Ansible
else
    echo "$ANSIBLE_PASSWORD"
    exit 0
fi
