# Codex desktop app (addition to the existing Codex page)

> Drop-in section for docs.merge.dev/merge-gateway/features/use-in-your-ide/codex. It assumes the provider block from **Configure Codex** is already in place and does not repeat it.

## Use in the Codex desktop app

The Codex desktop app does not read custom model providers from `config.toml` in its model picker. Enabling Gateway in the app requires a community patch that adds a provider selector. The patch modifies the Codex app and must be re-applied after app updates.

This section builds on the `[model_providers.merge-gateway]` block from **Configure Codex** above.

#### Point Codex at a model catalog

Add this top-level key to `~/.codex/config.toml` so the app can list Gateway models. Replace `<username>` with your macOS username:

```toml
model_catalog_json = "/Users/<username>/.codex/model-catalogs/custom.json"
```

The generated catalog sets `auto_review_model_override` on each Gateway entry. Codex then uses that Gateway model for automatic approval review instead of requesting the unavailable internal `openai/codex-auto-review` model.

#### Make the API key available to the app

macOS GUI apps do not read your shell profile, so the `export` from Configure Codex does not reach the app. Set the key at the login-session level with a LaunchAgent at `~/Library/LaunchAgents/dev.merge.gateway.env.plist`:

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

Load it, then confirm the app can see the key:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/dev.merge.gateway.env.plist
launchctl getenv MERGE_GATEWAY_API_KEY
```

#### Apply the desktop patch

Download the patch and run it. It backs up the app bundle and injects the provider selector:

```bash
python3 patch_chatgpt_providers.py
```

#### Map models to the provider

Create `~/.codex/desktop-model-providers.json`. The patch reads this to show the provider and route each slug to it. Add one line per model:

```json
{
  "version": 1,
  "default_provider": "openai",
  "providers": [
    { "id": "openai", "label": "ChatGPT / OpenAI", "description": "Signed-in ChatGPT account" },
    { "id": "merge-gateway", "label": "Merge Gateway", "description": "Uses [model_providers.merge-gateway]" }
  ],
  "model_providers": {
    "zai/glm-5.2": "merge-gateway",
    "anthropic/claude-opus-4-8": "merge-gateway"
  }
}
```

#### Build the model catalog

Run the catalog builder to add your Gateway models to the picker:

```bash
python3 build_catalog.py
```

#### Restart and select

Quit the app with `Cmd+Q` and reopen it. The picker shows a Merge Gateway provider with your models. The selected provider applies to new conversations.

## Caveats (desktop app)

#### Re-apply the patch after app updates

Codex app updates remove the patch, so the provider selector disappears. Re-run `python3 patch_chatgpt_providers.py` and restart the app. Your config, provider map, catalog, and API key are unaffected.

#### Adding more models

Add the slug to `desktop-model-providers.json` and to the `MERGE_MODELS` list in `build_catalog.py`, re-run the builder, then restart the app. List available slugs with `GET /v1/models`.

#### Requests fail, or `wire_api = "chat" is no longer supported`

Set `wire_api = "responses"` on the `[model_providers.merge-gateway]` block (or omit it — `responses` is Codex's default). The Gateway supports the Responses API, including tool calls, at `/v1/openai/responses`. Do **not** set `wire_api = "chat"` — recent Codex builds reject it and refuse to load the config. After editing, fully quit and reopen the app.

#### Tool calls fail after an approval request

If the error mentions `openai/codex-auto-review`, or ends with `stream disconnected before completion` and missing `tool_call_id` responses, regenerate the catalog with `python3 build_catalog.py`, fully quit and reopen Codex, then start a new task. The generated entries set `auto_review_model_override` to a Gateway model that can service the approval review.
