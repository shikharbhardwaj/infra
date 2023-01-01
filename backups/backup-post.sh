#!/bin/bash

cur_date="$(date +%F)"
bucket_name="cardstock"
backup_prefix="backups"

export $(bw list --folderid "e7f971ab-d4a0-4a2c-a966-6d0251f012f2" --search "OVH S3" items | jq -r ".[].notes")

# Do the sync
s5cmd sync "./inflight/$cur_date" "s3://$bucket_name/$backup_prefix/"