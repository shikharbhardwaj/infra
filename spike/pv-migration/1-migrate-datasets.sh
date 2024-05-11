#!/bin/bash

# Set the source and destination ZFS pool names
source_pool="..."
destination_pool="..."

# Read each line from the input file
while IFS=$'\t' read -r namespace pv pvc; do
    # Extract relevant parts from the input line
    namespace="${namespace// /}"   # Trim any extra spaces
    pvc="${pvc// /}"               # Trim any extra spaces
    pv="${pv// /}"               # Trim any extra spaces

    # Formulate the ZFS send and receive command
    send_command="zfs send ${source_pool}/${pvc}@manual-20240510"
    recv_command="zfs recv ${destination_pool}/${namespace}-${pv}"

    # Execute the ZFS send | ZFS recv command
    echo "Executing: $send_command | $recv_command"
    # Uncomment to run the migration
    # $send_command | $recv_command

    # Check the exit status of the previous command
    if [ $? -ne 0 ]; then
        echo "Error executing ZFS send | recv for ${pvc}"
    fi

done < nfs-pvc-list.txt