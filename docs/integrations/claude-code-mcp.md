# Claude Code MCP - post-consolidation config

The platform's MCP server moved from `~/Dayz/dayz-stack/` to `~/Dayz/dayz/platform/`. Update `~/.claude.json` (Claude Code's MCP config) to point at the new location.

## New config block

```json
{
  "mcpServers": {
    "dayz-kb": {
      "command": "C:\\Users\\<user>\\Dayz\\dayz\\platform\\.venv\\Scripts\\python.exe",
      "args": ["-m", "dayzstack_kb.mcp.server"],
      "cwd": "C:\\Users\\<user>\\Dayz\\dayz\\platform",
      "env": {
        "DAYZSTACK_DB_HOST": "localhost",
        "DAYZSTACK_DB_PORT": "5436",
        "DAYZSTACK_DB_NAME": "dayzstack",
        "DAYZSTACK_DB_USER": "dayzstack",
        "DAYZSTACK_DB_PASSWORD": "dayzstack"
      }
    }
  }
}
```

## What changed

- `command` and `cwd` paths: `~/Dayz/dayz-stack/` -> `~/Dayz/dayz/platform/`
- Everything else (module path, env vars, DB config) stays the same - the consolidation moved files but didn't change runtime contracts.

## Restart Claude Code

After updating the config:
1. Fully quit Claude Code (taskbar tray + close all windows)
2. Relaunch
3. Verify the 7 MCP tools appear (4 KB + 3 config)

## Verification

In any Claude Code session, ask:
```
Use dayz-kb to look up modded class MissionGameplay.
```

If the tool fires and returns hybrid-search results, the config is working.

If it doesn't, check Claude Code's MCP logs for connection errors. Most common failure: stale `.venv/` reference (recreate the venv via `cd platform && uv venv && uv pip install -e ./shared -e ./kb -e ./intel -e ./config_mod -e ./tools`).
