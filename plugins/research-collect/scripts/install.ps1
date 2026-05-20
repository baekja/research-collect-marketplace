# research-collect installer for Windows PowerShell.
# Mirrors install.sh: register MCP servers and pip install -e the repo root.

$ErrorActionPreference = "Stop"

Write-Host "[research-collect] Registering MCP servers..."

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Error "claude CLI not found. Install Claude Code first."
    exit 1
}

$firecrawlKey = if ($env:FIRECRAWL_API_KEY) { $env:FIRECRAWL_API_KEY } else { "set_me_in_env" }

Write-Host "  -> firecrawl-mcp (optional, recommended)"
try {
    claude mcp add firecrawl npx -- -y firecrawl-mcp -e "FIRECRAWL_API_KEY=$firecrawlKey"
} catch {
    Write-Warning "firecrawl-mcp registration failed (already registered or npx unavailable). Continuing."
}

Write-Host "  -> zotero-mcp (required)"
try {
    claude mcp add zotero uvx -- zotero-mcp -e ZOTERO_LOCAL=true
} catch {
    Write-Warning "zotero-mcp registration failed (already registered or uvx unavailable). Continuing."
}

Write-Host "[research-collect] Installing Python deps..."
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
try {
    pip install -e $repoRoot
} catch {
    pip install -e .
}

Write-Host "[research-collect] Done. Please restart Claude Code."
Write-Host ""
Write-Host "Optional: edit .env to enable cloud mode and Unpaywall fallback."
