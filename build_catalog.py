#!/usr/bin/env python3
"""Build ~/.codex/model-catalogs/custom.json by exporting the bundled Codex
model catalog and appending the Merge Gateway models.

Run:  python3 build_catalog.py
Then make sure config.toml has:
    model_catalog_json = "/Users/<you>/.codex/model-catalogs/custom.json"
"""
import json
import os
import subprocess
import sys

CODEX_HOME = os.path.expanduser("~/.codex")
OUT_DIR = os.path.join(CODEX_HOME, "model-catalogs")
OUT_PATH = os.path.join(OUT_DIR, "custom.json")

# Where to find the `codex` binary. Tries the app bundle first (it is not on
# PATH by default), then falls back to a plain `codex` on PATH.
CODEX_CANDIDATES = [
    "/Applications/ChatGPT.app/Contents/Resources/codex",
    "codex",
]


def find_codex():
    import shutil
    for c in CODEX_CANDIDATES:
        if os.path.isfile(c) or shutil.which(c):
            return c
    sys.exit(
        "error: could not find the `codex` binary.\n"
        "Edit CODEX_CANDIDATES at the top of this script with its full path."
    )

# Models to add. Slugs must match what Merge Gateway expects.
# `template` is a substring used to pick an existing catalog entry to clone, so
# the new entry inherits every required field (supported_reasoning_levels, etc.).
MERGE_MODELS = [
    {
        "slug": "moonshot/kimi-k3",
        "display_name": "Kimi K3 (Merge Gateway)",
        "description": "MoonshotAI Kimi K3 via Merge Gateway.",
        "template": "gpt-5.6-sol",
    },
    {
        "slug": "openai/gpt-5.6-sol",
        "display_name": "GPT-5.6 Sol (Merge Gateway)",
        "description": "OpenAI GPT-5.6 Sol via Merge Gateway.",
        "template": "gpt-5.6-sol",
    },
    {
        "slug": "openai/gpt-5.6-terra",
        "display_name": "GPT-5.6 Terra (Merge Gateway)",
        "description": "OpenAI GPT-5.6 Terra via Merge Gateway.",
        "template": "gpt-5.6-terra",
    },
    {
        "slug": "zai/glm-5.2",
        "display_name": "GLM 5.2 (Merge Gateway)",
        "description": "Z.ai GLM 5.2 via Merge Gateway.",
        "template": "gpt-5.6-sol",
    },
    {
        "slug": "anthropic/claude-opus-4-8",
        "display_name": "Claude Opus 4.8 (Merge Gateway)",
        "description": "Anthropic Claude Opus 4.8 via Merge Gateway.",
        "template": "gpt-5.6-sol",
    },
    {
        "slug": "google/gemini-3.1-pro-preview",
        "display_name": "Gemini 3.1 Pro (Merge Gateway)",
        "description": "Google Gemini 3.1 Pro via Merge Gateway.",
        "template": "gpt-5.6-sol",
    },
    {
        "slug": "deepseek/deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro (Merge Gateway)",
        "description": "DeepSeek V4 Pro via Merge Gateway.",
        "template": "gpt-5.6-sol",
    },
    {
        "slug": "xai/grok-4.5",
        "display_name": "Grok 4.5 (Merge Gateway)",
        "description": "xAI Grok 4.5 via Merge Gateway.",
        "template": "gpt-5.6-sol",
    },
    {
        "slug": "qwen/qwen3.7-max",
        "display_name": "Qwen3.7 Max (Merge Gateway)",
        "description": "Alibaba Qwen3.7 Max via Merge Gateway.",
        "template": "gpt-5.6-sol",
    },
]

# Field-name candidates for cloning (real catalogs vary in exact key names).
ID_KEYS = ("slug", "id", "model", "model_id")
NAME_KEYS = ("display_name", "displayName", "name", "label", "title")
DESC_KEYS = ("description", "summary")


def export_bundled():
    """Return the bundled catalog as parsed JSON."""
    codex = find_codex()
    try:
        out = subprocess.check_output([codex, "debug", "models", "--bundled"])
    except FileNotFoundError:
        sys.exit(f"error: could not run `{codex}`. Check the path in CODEX_CANDIDATES.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"error: `codex debug models --bundled` failed (exit {e.returncode}).")
    return json.loads(out)


def find_model_list(catalog):
    """Return (container, key) so container[key] is the list of model entries.
    Handles a top-level list, or an object with a list under a common key."""
    if isinstance(catalog, list):
        return catalog, None
    if isinstance(catalog, dict):
        for key in ("models", "model_catalog", "catalog", "entries"):
            if isinstance(catalog.get(key), list):
                return catalog, key
    sys.exit(
        "error: could not locate the model list in the exported catalog.\n"
        "Inspect the output of `codex debug models --bundled` and adjust find_model_list()."
    )


def slug_of(entry):
    if isinstance(entry, dict):
        for k in ID_KEYS:
            if entry.get(k):
                return entry[k]
    return None


def pick_template(models, hint):
    """Return an existing entry to clone: first one whose id contains `hint`,
    else the first entry in the catalog."""
    for m in models:
        s = slug_of(m)
        if s and hint in s:
            return m
    return models[0] if models else None


def make_entry(template, spec):
    """Clone `template` (a real catalog entry) and override its id/name/desc
    fields so it points at the Merge Gateway slug. Inherits all other required
    fields (supported_reasoning_levels, capabilities, etc.)."""
    import copy
    e = copy.deepcopy(template)
    for k in ID_KEYS:
        if k in e:
            e[k] = spec["slug"]
    for k in NAME_KEYS:
        if k in e:
            e[k] = spec["display_name"]
    for k in DESC_KEYS:
        if k in e:
            e[k] = spec["description"]
    return e


def main():
    catalog = export_bundled()
    container, key = find_model_list(catalog)
    models = container if key is None else container[key]

    if not models:
        sys.exit("error: the exported catalog has no model entries to use as a template.")

    print(f"Catalog has {len(models)} models. Example entry keys: {sorted(models[0].keys())}\n")

    existing = {slug_of(m) for m in models}
    added = []
    for spec in MERGE_MODELS:
        if spec["slug"] in existing:
            print(f"skip (already present): {spec['slug']}")
            continue
        template = pick_template(models, spec["template"])
        entry = make_entry(template, spec)
        models.append(entry)
        added.append(spec["slug"])
        print(f"added: {spec['slug']}  (cloned from '{slug_of(template)}')")

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(catalog, f, indent=2)

    print(f"\nWrote {OUT_PATH}")
    print(f"Added: {', '.join(added) if added else '(none — all already present)'}")


if __name__ == "__main__":
    main()
