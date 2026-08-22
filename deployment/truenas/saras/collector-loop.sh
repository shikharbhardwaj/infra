#!/usr/bin/env bash
# Emits HBA + per-drive temperatures as Prometheus textfile metrics for
# node_exporter's --collector.textfile.directory. Runs inside the TrueNAS
# monitoring Custom App's privileged `metrics-collector` container as root, so
# the HBA tool needs no sudo (unlike the interactive
# `sudo /mnt/main/apps/hba-temp/sas2308_temp /dev/mpt2ctl`).
#
# Written atomically (temp file + rename on the same fs) so node_exporter never
# reads a half-written file. See deployment/truenas/saras/README.md.
set -u

TEXTFILE_DIR="${TEXTFILE_DIR:-/textfile}"
HBA_TOOL="${HBA_TOOL:-/opt/hba-temp/sas2308_temp}"
HBA_DEV="${HBA_DEV:-/dev/mpt2ctl}"
INTERVAL="${INTERVAL:-60}"
OUT="${TEXTFILE_DIR}/truenas.prom"

# Pull the first (possibly decimal) number out of a tool's output - the HBA
# tool and smartctl both surround the value with labels/units.
first_number() { grep -oE '[0-9]+([.][0-9]+)?' | head -n1; }

collect() {
  tmp="${TEXTFILE_DIR}/.truenas.prom.$$"
  {
    echo "# HELP hba_temperature_celsius LSI SAS2308 HBA temperature (sas2308_temp tool)."
    echo "# TYPE hba_temperature_celsius gauge"
    hba="$("$HBA_TOOL" "$HBA_DEV" 2>/dev/null | first_number)"
    if [ -n "$hba" ]; then
      echo "hba_temperature_celsius{controller=\"sas2308\"} ${hba}"
    fi

    echo "# HELP disk_temperature_celsius Per-drive temperature via smartctl."
    echo "# TYPE disk_temperature_celsius gauge"
    # `smartctl --scan` prints "<dev> -d <type> # <comment>". `-n standby`
    # returns without spinning up a sleeping disk - it just prints no
    # attributes, so that disk is naturally skipped this cycle (no stale value).
    smartctl --scan 2>/dev/null | while read -r dev _dash dtype _rest; do
      [ -n "$dev" ] || continue
      a="$(smartctl -A -n standby -d "${dtype:-auto}" "$dev" 2>/dev/null)"
      # SAS: "Current Drive Temperature:  34 C"; NVMe: "Temperature: 40 Celsius";
      # SATA: SMART attribute 194 Temperature_Celsius (raw value, column 10).
      temp="$(printf '%s\n' "$a" | awk '/Current Drive Temperature/ {print $4; exit}')"
      [ -n "$temp" ] || temp="$(printf '%s\n' "$a" | awk '/^Temperature:/ {print $2; exit}')"
      [ -n "$temp" ] || temp="$(printf '%s\n' "$a" | awk '$1==194 {print $10; exit}')"
      temp="$(printf '%s' "$temp" | first_number)"
      [ -n "$temp" ] || continue
      echo "disk_temperature_celsius{disk=\"$(basename "$dev")\"} ${temp}"
    done
  } >"$tmp" 2>/dev/null
  mv -f "$tmp" "$OUT"
}

while true; do
  collect
  sleep "$INTERVAL"
done
