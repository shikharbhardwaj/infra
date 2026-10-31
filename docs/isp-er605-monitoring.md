# Home WAN monitoring (TP-Link ER605, dual WAN)

Goal: a Discord alert when either WAN goes down.

## How it works

- `blackbox_exporter` on **arete** (behind the ER605) pings four IPs. vmagent on
  tyr scrapes it over Tailscale (job `isp-wan`).
- ER605 **policy routing** pins each IP to one WAN with backup off, so a ping
  fails exactly when its WAN is down:

  | WAN | IPs |
  |---|---|
  | wan1 | `1.0.0.1`, `149.112.112.112` |
  | wan2 | `8.8.4.4`, `208.67.220.220` |

- vmalert records `isp:wan_up{wan}` (either IP answers) and `isp:internet_up`
  (any WAN up).
- Alerts:
  - **WAN down**: one WAN is out. The other WAN still carries Tailscale, so this
    is reported live.
  - **Home internet down**: both WANs are out. Probes go absent, so this one
    fires from tyr's side. It's skipped if thor is still reachable, because
    that means only arete is down.
- Dashboard: "Home Internet (ER605)".

## Setup

1. **ER605 policy routes**, set in the Omada controller under Settings →
   Transmission → Routing → Policy Routing:
   - Destination `1.0.0.1`, `149.112.112.112` → WAN1
   - Destination `8.8.4.4`, `208.67.220.220` → WAN2

   For both rules, **untick "Use the other WAN ports as backup"**. Don't use
   these IPs for anything else. To check, run `traceroute` to one IP of each
   pair from arete; they should leave via different ISPs.
2. Run `make configure-isp-probes`. vmagent reaches it via the existing
   `arete_tailscale_ip` secret.
