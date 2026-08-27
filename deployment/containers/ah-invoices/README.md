# ah-invoices

Albert Heijn receipt sync + analytics, with a monthly shopping-list suggester
planned as a follow-up. Upstream: https://github.com/salujayatharth/ah-api —
run from our hardened fork https://github.com/shikharbhardwaj/ah-api (see
commit `5980fcf` for the deltas: token file 0600, CORS opt-in, vendored
chart.js).

## One-time Albert Heijn login

The app talks to AH's unofficial app API and needs an OAuth token:

1. Open `https://login.ah.nl/secure/oauth/authorize?client_id=appie&redirect_uri=appie://login-exit&response_type=code`
2. Log in. The browser fails to open `appie://login-exit` — that's expected.
3. Copy the `code=...` value from the redirect URL in the address bar.
4. Paste it into the dashboard's auth form, or:
   `curl -X POST https://invoices.gliese.<domain>/receipts/auth -H 'Content-Type: application/json' -d '{"code": "..."}'`
5. Trigger a backfill: `POST /receipts/sync`

Tokens auto-refresh (~2h access, refresh token on disk). If refreshes ever
start failing, redo the browser login. All receipt data lands in
`data/receipts.db`; an API breakage pauses new data but loses nothing.

## Security posture

- **No authentication on the app itself.** The Traefik route is dual-host
  (`invoices.gliese.{{ oci_parent_host }}` / `invoices.{{ local_host }}`) but
  purchase history is personal — do not widen the exposure without putting an
  auth middleware (e.g. forward-auth / basicAuth) in front.
- The OAuth refresh token lives in `data/.tokens.json` (0600 in our fork).
  `data/` volume access == AH account access.
- No `PublishPort`: the container is only reachable on the `web` podman
  network, via Traefik.
- CORS is disabled by default in the fork (`CORS_ORIGINS` unset here).

## Data

Everything is in `data/` on gliese (SQLite `receipts.db` + `.tokens.json`).
Back this directory up like any other stateful container volume.
