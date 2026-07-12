# Obsidian plugin settings

Not templated — plugin `data.json` files are generated state (IDs, timestamps, UI state) mixed
in with the handful of settings that actually matter here, and hand-editing them risks
corrupting the plugin's store. Set these once through each plugin's settings UI instead.

## Copilot

Settings → Copilot:

- **Default chat model** → add a custom OpenAI-compatible endpoint:
  - Base URL: `https://litellm.gliese.{{ oci_parent_host }}/v1` (or `https://litellm.{{ local_host }}/v1`
    on the LAN)
  - API key: gliese's `litellm_master_key` (from `deployment/containers/secrets.yml` on gliese
    — copy the value, don't commit it anywhere)
  - Model name: `local-mac` for vault-grounded chat (see privacy note below); a
    `openrouter-frontier`-backed mode can be added separately for non-vault questions.
- **Embedding model**: leave on Copilot's local/built-in embedding option — do not point this
  at LiteLLM or any remote endpoint. Embedding the vault via a remote API leaks its contents
  even if the chat model itself is local.
- **MCP servers**: Settings → Copilot → MCP Servers → paste the contents of
  `deployment/mac/mcp/client-config.json` (with the vault path filled in).

## Smart Connections

Settings → Smart Connections:

- Embedding model: local (default), no API key — this plugin never needs to leave the machine.
- Excluded folders: exclude anything not meant for retrieval (e.g. templates, attachments) per
  your vault's structure.

## Privacy-critical rule

Retrieved vault chunks get injected into whatever prompt Copilot sends — LiteLLM only sees the
final prompt text, so it cannot distinguish "innocuous question that happens to include private
RAG context" from a genuinely innocuous one and route accordingly. **Keep the vault-chat mode
pinned to `local-mac`.** Only switch to an OpenRouter-backed mode for chats that deliberately
exclude vault context (e.g. general coding questions asked from within Obsidian).
