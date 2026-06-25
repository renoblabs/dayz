# DayZ Modding Project - AI IDE Guidelines

> This file is read by Claude Code, Cursor, Copilot, and most AI coding assistants.
> Droid uses `.factory/droids/` for custom agents that complement these guidelines.

## Project Structure

```
dayz/
|-- .claude/                    # Claude Code configuration
|   |-- CLAUDE.md              # This file - project guidelines
|   |-- skills/
|   |   `-- dayz-modding.md    # DayZ-specific knowledge base
|   |-- dayz-errors.jsonl      # Error capture log
|   `-- dayz-debugger.md       # Debugger subagent system prompt
|-- mods/                       # Source mod directories
|   |-- BossSignal/
|   |-- HiveApiMod/
|   `-- TrophyHunter/
|-- tools-extra/modctl/        # Build & deployment CLI
|-- dayz-mcp/                  # MCP server for DayZ dev tools
|-- output/                    # Built mod PBOs
`-- backends/                  # Backend API services
```

## DayZ Server Testing Protocol

### Before Any Code Changes
1. Check if the server is running: `Get-Process DayZServer_x64`
2. Stop server gracefully before rebuilds
3. Always rebuild affected mods: `python -m modctl -c mods.yaml build <modname>`

### After Code Changes
1. Rebuild the mod
2. Restart server via `modctl serve`
3. Wait for script log to show "OnMissionLoaded fired"
4. Check script_*.log for compile errors BEFORE attempting connection

### Critical File Paths
- **Server RPT Logs:** `C:\Program Files (x86)\Steam\steamapps\common\DayZServer\profiles\*.RPT`
- **Script Logs:** `C:\Program Files (x86)\Steam\steamapps\common\DayZServer\profiles\script_*.log`
- **Crash Logs:** `C:\Program Files (x86)\Steam\steamapps\common\DayZServer\profiles\crash_*.log`
- **Mission Files:** `C:\Program Files (x86)\Steam\steamapps\common\DayZServer\mpmissions\dayzOffline.chernarusplus\`
- **Server Config:** `C:\Program Files (x86)\Steam\steamapps\common\DayZServer\serverDZ.cfg`

## MANDATORY: Enforce Script Error Diagnosis

**Before attempting to diagnose ANY Enforce script compilation error, you MUST:**

1. **READ** `.claude/skills/dayz-modding.md` to check for known issues
2. **PARSE** the script log to identify the exact error type:
   - `Undefined function` - Function removed/renamed in DayZ version
   - `Can't find class` - Missing class or wrong namespace
   - `Bad type` - Type compatibility issue (often Param classes)
   - `No need to use 'Cast'` - Warning only, non-blocking
3. **CROSS-REFERENCE** with the known issues database before proposing fixes

## Build Commands

```powershell
# Build single mod
cd tools-extra/modctl
python -m modctl -c mods.yaml build bosssignal

# Build all mods
python -m modctl -c mods.yaml build bosssignal
python -m modctl -c mods.yaml build hiveapi
python -m modctl -c mods.yaml build trophyhunter

# Start server with all mods
python -m modctl -c mods.yaml serve
```

## Environment Variables

- `BOSSSIGNAL_SECRET` - Shared secret for BossSignal/TrophyHunter backend auth
- DayZ Tools path: `C:/Program Files (x86)/Steam/steamapps/common/DayZ Tools`
- DayZ Server path: `C:/Program Files (x86)/Steam/steamapps/common/DayZServer`

## DayZ Port Map (6700 range - avoid conflicts with other projects)

| Service | Port |
|---------|------|
| BossSignal backend | 6700 |
| HiveAPI backend | 6701 |
| Dashboard (Vite) | 6702 |
| Neo4j Bolt | 6703 |
| Neo4j Browser | 6704 |
| DayZ Server | 2302 (Steam standard) |

## Error Capture & Analysis

Capture server crashes to local database:
```bash
./capture-dayz-error.sh          # One-shot capture
./capture-dayz-error.sh --watch  # Continuous monitoring
```

Analyze captured errors:
```bash
python analyze_errors.py                  # JSON output
python analyze_errors.py --format markdown  # Human-readable
```

## MCP Tools (dayz-mcp/)

Run the MCP server:
```bash
cd dayz-mcp && pip install fastmcp && python -m server
```

Available tools:
- `unpack_pbo(pbo_path)` - Extract PBO contents
- `validate_enforce_syntax(source_dir)` - Test compile
- `analyze_mod_conflicts(mod_dirs)` - Check class conflicts
- `read_server_log(log_type)` - Read logs
- `get_known_issues()` - Get documented solutions

## Graph Memory (dayz-memory/)

Neo4j-backed causal knowledge graph. Stores errors, solutions, and patterns
with effectiveness tracking. Gets smarter over time.

```bash
# Start Neo4j
cd dayz-memory && docker compose up -d

# Seed with known issues from this session
python -m dayz_memory.seed

# Run memory MCP server
python -m dayz_memory

# Auto-capture errors from server logs
.\dayz-memory\hooks\auto_capture.ps1 -Watch
```

MCP tools: `store_error`, `store_solution`, `find_similar_errors`,
`get_causal_chain`, `track_fix_result`, `get_top_solutions`
