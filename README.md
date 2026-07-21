# Codex App + Merge Gateway

Use **[Merge Gateway](https://docs.merge.dev/merge-gateway/)** models (Claude, Gemini, GLM, DeepSeek, Grok, Qwen, Kimi, and 240+ more) directly inside the **Codex desktop app** — from the model picker in the UI, not just the CLI.

---

## The problem

The Codex CLI happily reads custom `[model_providers.*]` blocks from `~/.codex/config.toml`. **The desktop app does not** — its model picker only shows OpenAI's built-in models. Custom providers and profile files are invisible in the UI.

Two pieces fix this:

1. **A community patch** ([Keksuccino/Better-Codex-App-Custom-Provider-Support](https://github.com/Keksuccino/Better-Codex-App-Custom-Provider-Support)) that injects a **provider selector** into the app and reads a `desktop-model-providers.json` mapping.
2. **A custom model catalog** (`model_catalog_json`, a native Codex feature) that makes your Gateway model slugs appear as selectable models.

This repo gives you the config files, a catalog builder, and step-by-step instructions to wire both up.

> **Credit:** the app patch itself is **not** in this repo — it belongs to [Keksuccino](https://github.com/Keksuccino/Better-Codex-App-Custom-Provider-Support). Download it from there. This repo only provides the Merge Gateway configuration around it.

---

## What's in here

| Path | What it is |
|------|------------|
| `build_catalog.py` | Exports Codex's bundled model catalog and injects your Merge Gateway models (clones a real entry so every required field is present). |
| `desktop-model-providers.json` | Read by the app patch — declares the **Merge Gateway** provider and maps each model slug to it. Copy to `~/.codex/`. |
| `examples/config.snippet.toml` | The `config.toml` pieces to add (provider block + `model_catalog_json`). |
| `examples/dev.merge.gateway.env.plist.template` | LaunchAgent that feeds your API key to the GUI app. Fill in your key, then copy to `~/Library/LaunchAgents/`. |
| `profiles/*.config.toml` | Optional CLI profiles (`codex --profile ...`). Not needed for the app. |

---

## Prerequisites

- **macOS** with the ChatGPT / Codex desktop app installed
- A **[Merge Gateway API key](https://docs.merge.dev/merge-gateway/)** (looks like `mg_...`)
- **Python 3.9+** and **Node.js / npx** (the patch needs npx)

---

## Setup

### 1. Add the provider to `config.toml`

Merge the contents of [`examples/config.snippet.toml`](examples/config.snippet.toml) into your `~/.codex/config.toml` (don't overwrite the whole file). It adds:

```toml
model_catalog_json = "/Users/<YOUR-USERNAME>/.codex/model-catalogs/custom.json"

[model_providers.merge-gateway]
name = "Merge Gateway"
base_url = "https://api-gateway.merge.dev/v1/openai"
env_key = "MERGE_GATEWAY_API_KEY"
```

Replace `<YOUR-USERNAME>` with your macOS username (`echo $USER`).

### 2. Make your API key available to the GUI app

macOS GUI apps **don't** read `~/.zshrc`, so an `export` line alone won't work for the app. Set the key at the login-session level with a LaunchAgent:

```bash
# Fill in your key first:
cp examples/dev.merge.gateway.env.plist.template dev.merge.gateway.env.plist
# edit dev.merge.gateway.env.plist -> replace REPLACE_WITH_YOUR_MERGE_GATEWAY_KEY

mkdir -p ~/Library/LaunchAgents
cp dev.merge.gateway.env.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/dev.merge.gateway.env.plist

# Verify — should print your key:
launchctl getenv MERGE_GATEWAY_API_KEY
```

This re-runs at every login, so it survives reboots. (For CLI use, also add `export MERGE_GATEWAY_API_KEY="mg_..."` to `~/.zshrc`.)

### 3. Patch the app

Download `patch_chatgpt_providers.py` from the [upstream repo](https://github.com/Keksuccino/Better-Codex-App-Custom-Provider-Support), then:

```bash
python3 patch_chatgpt_providers.py
```

It backs up and modifies the app bundle to add the provider selector.

### 4. Install the provider map

```bash
cp desktop-model-providers.json ~/.codex/
```

### 5. Build the model catalog

```bash
python3 build_catalog.py
```

This finds your `codex` binary (inside the app bundle by default), exports the bundled catalog, injects the Merge Gateway models, and writes `~/.codex/model-catalogs/custom.json`.

### 6. Restart the app

**Fully quit** (`Cmd+Q`) and reopen. Open the model picker → you'll see a **Merge Gateway** provider with all the models below.

> The patch applies the chosen provider to **new** conversations only — you can't switch provider mid-thread.

---

## Included models

All slugs are verified against the live Gateway catalog.

| Display name | Slug |
|---|---|
| Kimi K3 | `moonshot/kimi-k3` |
| GPT-5.6 Sol | `openai/gpt-5.6-sol` |
| GPT-5.6 Terra | `openai/gpt-5.6-terra` |
| GLM 5.2 | `zai/glm-5.2` |
| Claude Opus 4.8 | `anthropic/claude-opus-4-8` |
| Gemini 3.1 Pro | `google/gemini-3.1-pro-preview` |
| DeepSeek V4 Pro | `deepseek/deepseek-v4-pro` |
| Grok 4.5 | `xai/grok-4.5` |
| Qwen3.7 Max | `qwen/qwen3.7-max` |

---

## Adding more models

**1. Find the slug.** List everything your key can reach:

```bash
curl -s https://api-gateway.merge.dev/v1/openai/models \
  -H "Authorization: Bearer $MERGE_GATEWAY_API_KEY" \
  | python3 -m json.tool | grep '"id"'
```

**2. Add it to `build_catalog.py`.** Append an entry to the `MERGE_MODELS` list:

```python
{
    "slug": "provider/model-name",          # exact slug from the catalog
    "display_name": "My Model (Merge Gateway)",
    "description": "...",
    "template": "gpt-5.6-sol",              # existing entry to clone field-shape from
},
```

**3. Map it to the provider** in `desktop-model-providers.json` under `model_providers`:

```json
"provider/model-name": "merge-gateway"
```

**4. Rebuild and restart:**

```bash
cp desktop-model-providers.json ~/.codex/
python3 build_catalog.py
# Cmd+Q and reopen the app
```

The `template` field matters: `build_catalog.py` **clones** that existing catalog entry so your new model inherits every required field (`supported_reasoning_levels`, `context_window`, etc.). Pick a template with similar capabilities.

---

## ⚠️ When the Codex app updates

**App updates overwrite the patch — the provider selector will disappear.** After any Codex app update:

```bash
python3 patch_chatgpt_providers.py   # re-apply the patch
# then fully quit and reopen the app
```

Your `config.toml`, `desktop-model-providers.json`, catalog, and API key are untouched by updates — **only the patch needs re-applying.** If a major app update changes internals, check the [upstream repo](https://github.com/Keksuccino/Better-Codex-App-Custom-Provider-Support) for a refreshed patch.

---

## Optional: CLI profiles

For the `codex` CLI (not the app), the `profiles/` files let you launch straight into a model:

```bash
cp profiles/*.config.toml ~/.codex/
codex --profile merge_gpt56_sol
```

Each is a standalone profile file (Codex 0.134+ rejects `[profiles.x]` tables inside `config.toml`).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| **`missing field '...'` when parsing catalog** | Your entry is missing a required field. Make sure it uses a valid `template` slug so `build_catalog.py` can clone a complete entry. |
| **Merge models don't appear, only OpenAI ones** | Catalog failed to load (see the error toast) or `model_catalog_json` path is wrong. Check the path and re-run `build_catalog.py`. |
| **Provider selector missing entirely** | Patch not applied or wiped by an update — re-run `patch_chatgpt_providers.py`. |
| **Requests fail with a format error** | Uncomment `wire_api = "chat"` in the provider block. |
| **Auth errors / key not found** | Run `launchctl getenv MERGE_GATEWAY_API_KEY`. If empty, redo step 2 and fully restart the app. |
| **`codex` not found when building catalog** | Edit `CODEX_CANDIDATES` at the top of `build_catalog.py` with the full path to your `codex` binary. |

---

## Security

- **Never commit your API key.** The real key lives in `dev.merge.gateway.env.plist` and your personal `config.toml` — both are in `.gitignore`. Only the `.template` (with a placeholder) is tracked.
- The generated `custom.json` and `model-catalogs/` are git-ignored (machine-specific).

---

## Disclaimer

The app patch is an **unofficial community modification** of the Codex desktop app, maintained [here](https://github.com/Keksuccino/Better-Codex-App-Custom-Provider-Support). It modifies the app bundle and must be re-applied after updates. Use at your own risk. This repo is not affiliated with OpenAI or Merge.
