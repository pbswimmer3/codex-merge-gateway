# Use Merge Gateway in Codex

Merge Gateway is OpenAI-compatible, so you can route Codex through it and use any model in the Gateway catalog. This guide covers both the Codex CLI and the Codex desktop app.

## Prerequisites

- A Merge Gateway API key (format `mg_...`)
- macOS with Codex installed (CLI, desktop app, or both)
- Python 3.9 or newer

## Part A: Codex CLI

The CLI reads custom providers directly from `~/.codex/config.toml`. No extra tooling is required.

### 1. Define the provider

Add this block to `~/.codex/config.toml`:

```toml
[model_providers.merge-gateway]
name = "Merge Gateway"
base_url = "https://api-gateway.merge.dev/v1/openai"
env_key = "MERGE_GATEWAY_API_KEY"
```

If model requests fail with a request-format error, add `wire_api = "chat"` to the block. The Gateway `/v1/openai` endpoint uses the OpenAI chat-completions format.

### 2. Set the API key

Export the key in your shell profile (`~/.zshrc`, `~/.bashrc`, or `~/.config/fish/config.fish`):

```bash
export MERGE_GATEWAY_API_KEY="mg_your_key"
```

### 3. Create a profile

Codex 0.134 and later reject `[profiles.x]` tables inside `config.toml`. Each profile is a separate file next to `config.toml`. Create `~/.codex/merge_glm.config.toml`:

```toml
model_provider = "merge-gateway"
model = "zai/glm-5.2"
model_reasoning_effort = "medium"
```

Use any `provider/model` slug from the Gateway catalog for the `model` value.

### 4. Launch

```bash
codex --profile merge_glm
```

Requests appear in your Gateway dashboard within seconds.

## Part B: Codex desktop app

> The Codex desktop app does not read custom providers from `config.toml` in its model picker. Enabling this requires a community patch that modifies the Codex app. The patch is maintained outside of OpenAI and must be re-applied after Codex app updates. Treat this path as experimental.

The app needs three things: the provider block from Part A, a provider map the patch reads, and a model catalog that lists your Gateway models.

### 1. Define the provider

Add the `[model_providers.merge-gateway]` block from Part A to `~/.codex/config.toml`, then add this top-level key so Codex loads a catalog that includes your Gateway models. Replace `<YOUR-USERNAME>` with your macOS username:

```toml
model_catalog_json = "/Users/<YOUR-USERNAME>/.codex/model-catalogs/custom.json"
```

### 2. Make the API key available to the app

macOS GUI apps do not read `~/.zshrc`, so an `export` line does not reach the app. Set the key at the login-session level with a LaunchAgent so it persists across restarts.

Create `~/Library/LaunchAgents/dev.merge.gateway.env.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>dev.merge.gateway.env</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/launchctl</string>
        <string>setenv</string>
        <string>MERGE_GATEWAY_API_KEY</string>
        <string>mg_your_key</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

Load it and confirm:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/dev.merge.gateway.env.plist
launchctl getenv MERGE_GATEWAY_API_KEY
```

### 3. Apply the desktop patch

Download the patch and run it:

```bash
python3 patch_chatgpt_providers.py
```

The patch backs up the app bundle, injects a provider selector into the model menu, and reads the provider map from the next step.

### 4. Install the provider map

Create `~/.codex/desktop-model-providers.json`. This declares the Merge Gateway provider in the app and maps each model slug to it:

```json
{
  "version": 1,
  "default_provider": "openai",
  "providers": [
    { "id": "openai", "label": "ChatGPT / OpenAI", "description": "Uses your signed-in ChatGPT account" },
    { "id": "merge-gateway", "label": "Merge Gateway", "description": "Uses [model_providers.merge-gateway] from config.toml" }
  ],
  "model_providers": {
    "zai/glm-5.2": "merge-gateway",
    "anthropic/claude-opus-4-8": "merge-gateway",
    "google/gemini-3.1-pro-preview": "merge-gateway"
  }
}
```

Add one line under `model_providers` for every model you want to route through Gateway.

### 5. Build the model catalog

The catalog makes your Gateway slugs appear as selectable models. Run the catalog builder:

```bash
python3 build_catalog.py
```

The builder exports the bundled Codex catalog, clones an existing entry for each Gateway model so every required field is present, and writes `~/.codex/model-catalogs/custom.json`.

### 6. Restart the app

Fully quit Codex with `Cmd+Q` and reopen it. The model picker now shows a Merge Gateway provider with your models. The selected provider applies to new conversations only.

## Adding more models

1. Find the slug:

```bash
curl -s https://api-gateway.merge.dev/v1/openai/models \
  -H "Authorization: Bearer $MERGE_GATEWAY_API_KEY" \
  | python3 -m json.tool | grep '"id"'
```

2. Add the slug to `desktop-model-providers.json` under `model_providers`.
3. Add an entry to the `MERGE_MODELS` list in `build_catalog.py`.
4. Re-run `build_catalog.py`, then fully restart the app.

## Updating the Codex app

Codex app updates overwrite the desktop patch, so the provider selector disappears after an update. Re-apply the patch and restart:

```bash
python3 patch_chatgpt_providers.py
```

Your `config.toml`, provider map, catalog, and API key are not affected by app updates. Only the patch needs re-applying.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Only OpenAI models appear in the app | The catalog failed to load or `model_catalog_json` points at the wrong path. Check the error toast and re-run `build_catalog.py`. |
| Provider selector missing | The patch is not applied, or an app update removed it. Re-apply the patch. |
| Request-format error | Add `wire_api = "chat"` to the provider block. |
| Auth error or key not found | Run `launchctl getenv MERGE_GATEWAY_API_KEY`. If empty, reload the LaunchAgent and restart the app. |
