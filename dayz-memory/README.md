# DayZ Memory - Graph-Based Knowledge System

A Neo4j-backed MCP server that builds causal maps of DayZ modding errors,
fixes, and patterns. Any AI IDE (Droid, Claude Code, Cursor) can query
the shared memory to avoid repeating mistakes.

## Quick Start

### 1. Start Neo4j

```bash
cd dayz-memory
docker compose up -d
```

Neo4j Browser: http://localhost:7474 (login: neo4j / the password you set in `NEO4J_PASSWORD`)

### 2. Install Dependencies

```bash
pip install fastmcp neo4j
```

### 3. Seed with Known Issues

```bash
python -m dayz_memory.seed
```

This populates the graph with all DayZ 1.29 issues we've already solved
(GetStamina, Param2, path aliases, HTTP blocking, PBO caching).

### 4. Run the MCP Server

```bash
python -m dayz_memory
```

## MCP Tools Available

### Store
- `store_error` - Capture a DayZ error with metadata
- `store_solution` - Record a fix and link it to the error
- `store_pattern` - Save working/broken Enforce script patterns
- `link_cause` - Create causal relationships (A CAUSES B)

### Search
- `search_errors` - Full-text search across all errors
- `find_similar_errors` - Find previously solved similar errors
- `get_causal_chain` - Traverse upstream causes and downstream effects

### Track
- `track_fix_result` - Record whether a solution worked
- `get_top_solutions` - Ranked list by effectiveness score

### Session
- `start_session` - Begin a debug session (loads recent context)
- `get_stats` - Graph statistics

## IDE Integration

### Droid (Factory)

Add to `.factory/droids/` or use the `dayz-debug` droid.

### Claude Code

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "dayz-memory": {
      "command": "python",
      "args": ["-m", "dayz_memory"],
      "cwd": "C:\\Users\\<user>\\Dayz\\dayz\\dayz-memory",
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "<your-neo4j-password>",
        "PROJECT_CONTEXT": "dayz-mod-<org>"
      }
    }
  }
}
```

### Auto-Capture

Run the hook to watch for new errors:

```powershell
.\hooks\auto_capture.ps1 -Watch
```

## Graph Structure

```
[DayZError: "GetStamina undefined"]
    ←SOLVES-- [Solution: "Comment out, removed in 1.29"]
    ←CAUSES-- [DayZError: "Server hangs on world load"]
                  ←SOLVES-- [Solution: "Defer with CallLater"]

[EnforceScript: "CallLater pattern"]
    works: true
    category: "lifecycle"
```

## How It Gets Smarter

1. **Error captured** -> stored as DayZError node
2. **Fix applied** -> stored as Solution, linked to error
3. **Result tracked** -> effectiveness score updated
4. **Next time same error** -> AI searches graph, finds proven fix
5. **Causal chains** -> AI traces root causes across mod boundaries
