#!/usr/bin/env bash
set -e
echo "[research-collect] Registering MCP servers..."

if ! command -v claude &> /dev/null; then
  echo "ERROR: claude CLI not found. Install Claude Code first."
  exit 1
fi

echo "  → firecrawl-mcp (optional, recommended)"
claude mcp add firecrawl npx -- -y firecrawl-mcp \
  -e FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY:-"set_me_in_env"} || true

echo "  → zotero-mcp (required)"
claude mcp add zotero uvx -- zotero-mcp -e ZOTERO_LOCAL=true || true

echo "[research-collect] Installing Python deps..."
pip install -e "$(dirname "$0")/../../.." || pip install -e "."

echo "[research-collect] Done. Please restart Claude Code."
echo ""
echo "Optional: edit .env to enable cloud mode and Unpaywall fallback."
