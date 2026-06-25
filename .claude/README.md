# DayZ Modding Project

AI-friendly repo for DayZ mod development with modctl build tooling.

## AI IDE Integration

This repo is configured for use with any AI coding assistant:
- **Droid**: `.factory/droids/` for custom agents
- **Claude Code**: `.claude/` directory with skills and guidelines
- **Cursor/Copilot**: Uses CLAUDE.md as context (most AI tools read this)

### Key Files for AI Context

| File | Purpose |
|------|---------|
| `.claude/CLAUDE.md` | Project structure and mandatory protocols |
| `.claude/skills/dayz-modding.md` | Top 10 known DayZ issues with fixes |
| `.claude/dayz-debugger.md` | Specialized debugger agent system prompt |
| `docs/modding-source/dayz-modding-patterns.md` | Extended patterns library |

### MCP Server

DayZ dev tools available via MCP at `dayz-mcp/`:

```bash
cd dayz-mcp
pip install fastmcp
python -m server
```

Tools: `unpack_pbo`, `validate_enforce_syntax`, `analyze_mod_conflicts`, `read_server_log`, `get_known_issues`

### Error Capture

```bash
# Capture server crash to local log
./capture-dayz-error.sh

# Analyze captured errors
python analyze_errors.py --format markdown
```

## Build Commands

```powershell
cd tools-extra/modctl

# Build single mod
python -m modctl -c mods.yaml build bosssignal

# Build all mods
python -m modctl -c mods.yaml build bosssignal
python -m modctl -c mods.yaml build hiveapi
python -m modctl -c mods.yaml build trophyhunter

# Start server
python -m modctl -c mods.yaml serve
```

## Mods

| Mod | Purpose | Status |
|-----|---------|--------|
| BossSignal | Boss spawn/kill event tracking | Working |
| HiveApiMod | Cross-server character persistence | Working |
| TrophyHunter | Trophy awards for boss kills | Working |

## Directories

```
dayz/
|-- .claude/           # AI context files
|-- dayz-mcp/          # MCP server for DayZ tools
|-- mods/              # Mod source code
|-- tools-extra/modctl/# Build CLI
|-- backends/          # API backends
|-- frontends/         # Web dashboards
|-- platform/          # Knowledge base MCP server
`-- output/            # Built PBOs
```
