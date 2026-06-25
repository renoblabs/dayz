# DayZ Server Launcher Guide

Welcome to the crash-resistant launcher system. Because DayZ modding crashes are a fact of life.

## Quick Start

### For rapid testing (crashes immediately good to know)
```powershell
.\quick_test.ps1
```
- Builds once
- Ships `bosssignal` and `markscontent` by default
- Starts server once  
- Monitors for 2 minutes
- Exits on first crash with diagnosis
- Perfect for "did I break it" checks

### For actual development work
```powershell
.\launch_with_recovery.ps1
```
- Auto-restarts on crash
- Runs diagnosis after each crash
- Max 10 retries by default
- Won't hang for hours (10 min timeout per attempt)
- Once server is READY, monitors continuously

### Skip rebuild (you already built)
```powershell
.\quick_test.ps1 -NoBuild
.\launch_with_recovery.ps1 -SkipBuild
```

### Test a specific mod set
```powershell
.\quick_test.ps1 -Mods markscontent
.\launch_with_recovery.ps1 -Mods bosssignal,markscontent
```

### Customize retry behavior
```powershell
# More aggressive - 20 attempts, 5 min timeout
.\launch_with_recovery.ps1 -MaxRetries 20 -MonitorTimeoutSeconds 300

# Patient mode - 5 attempts, 15 min timeout  
.\launch_with_recovery.ps1 -MaxRetries 5 -MonitorTimeoutSeconds 900
```

## What The Launcher Does

### Build Phase
1. Uses `modctl ship <mod>` for each requested mod if available
2. Falls back to `build-pipeline\build.bat` 
3. Can skip with `-SkipBuild` flag

### Start Phase
1. Kills any existing DayZ server processes
2. Starts server via `modctl serve --detached` (or direct exe)
3. Waits for process to spawn

### Monitor Phase
Uses `monitor_dayz.ps1` to detect:
- **READY**: Port 2302 is accepting connections -> SUCCESS
- **HANG**: "ponds" keyword stuck in RPT for >2 minutes -> RESTART
- **CRASH**: Process exited unexpectedly -> RESTART
- **TIMEOUT**: No READY signal after 10 minutes -> RESTART

### Recovery Phase
On crash/hang:
1. Runs `modctl diagnose` to parse the latest RPT log
2. Shows known error patterns with suggested fixes
3. Waits 5 seconds (crash cooldown)
4. Restarts from Build Phase

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Server started successfully |
| 1 | Fatal error (build failed, max retries, or QuickFail) |

## Diagnosis Output

After each crash, you'll see:
```
[WARN] === DIAGNOSIS ===
ERROR: Undefined variable 'Param2' in HiveApiCharacterSync.c:45
  Suggested fix: Check prefix mismatch in config.cpp
ERROR: Missing requiredAddons: Community_Framework
  Suggested fix: Add "Community_Framework" to requiredAddons[] in config.cpp
[WARN] === END DIAGNOSIS ===
```

This is parsed from your RPT logs using modctl's rule library at:
`tools-extra/modctl/modctl/rules/enforce.yaml`

## Monitoring Script Details

`monitor_dayz.ps1` watches for:
- **Port 2302 connectivity** (server is up)
- **"ponds" keyword in RPT** (common hang point during world init)

You can customize:
- `$pondsTimeout = 120` - how long to wait on "ponds" before declaring hang
- `$maxTotalTime = 600` - max time before monitor gives up entirely

## When To Use Each Launcher

| Scenario | Script | Flags |
|----------|--------|-------|
| Quick compile check | `quick_test.ps1` | |
| Already built, just test | `quick_test.ps1 -NoBuild` | |
| MarksContent only | `quick_test.ps1` | `-Mods markscontent` |
| Dev session (expect crashes) | `launch_with_recovery.ps1` | |
| Long modding session | `launch_with_recovery.ps1 -MaxRetries 20` | |
| Testing specific build | `launch_with_recovery.ps1 -SkipBuild` | |

## Troubleshooting

### "Monitor script not found"
- Launcher will fall back to basic process monitoring
- You won't get hang detection, only crash detection

### "modctl not found"  
- Launcher will use `build.bat` instead
- Diagnosis will be skipped
- Server start will use direct exe launch

### Infinite crash loop
- Check the diagnosis output for patterns
- Common issues:
  - Prefix mismatch (see `.claude/skills/dayz-modding.md`)
  - Missing `requiredAddons` for Community_Framework
  - Scripts in wrong module (Mission code in World module)

### Server starts but mods don't load
- Check `output/@ModName` exists and has .pbo files
- Verify `build-pipeline/keys/ModName.bikey` is present
- Check server is loading the mod (see RPT log header)

## Integration with modctl

This launcher wraps `modctl serve` but adds:
- Crash recovery loop
- Integrated diagnosis
- Configurable timeouts
- Progress logging

If you prefer raw modctl:
```powershell
cd tools-extra/modctl
python -m modctl ship bosssignal  # build + deploy
python -m modctl serve --detached # start server
python -m modctl tail              # find RPT log
python -m modctl diagnose          # parse errors
python -m modctl restart           # graceful restart
```

## Next Steps

1. Run `quick_test.ps1` to see current state
2. If it crashes, read the diagnosis output
3. Fix the issues surfaced by the diagnosis (cross-reference `.claude/skills/dayz-modding.md`)
4. Re-run quick_test until it reaches READY
5. Switch to `launch_with_recovery.ps1` for longer sessions
6. Use `modctl watch bosssignal` for auto-rebuild on file changes

Good luck out there. The crashes are normal. The launcher handles them. You just fix the code.
