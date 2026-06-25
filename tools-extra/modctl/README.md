# modctl

DayZ mod development workflow CLI. Build, deploy, and ship mods end-to-end
from a single command. Designed for Claude Code orchestration.

See design: `docs/superpowers/specs/2026-04-23-modctl-design.md`

## Install (development)

```bash
cd tools/modctl
pip install -e ".[dev]"
```

Then `modctl` is available on your PATH.

## Commands

### Lifecycle

#### `modctl version`
Print installed version.

#### `modctl doctor`
Verify toolchain health: DayZ Tools, DayZ Server, signing keys.

```bash
modctl doctor                  # human output
modctl --json doctor           # structured output for Claude Code
```

### Mod pipeline

#### `modctl build <mod>`
Compile + sign a mod into a signed PBO.

```bash
modctl build bosssignal
```

Output lands at `output/<mod_folder>/addons/<PboName>.pbo`.

#### `modctl deploy <mod>`
Copy a built PBO (+ .bisign + .bikey) to the local DayZ Server. When
`defaults.deploy_client_workshop` is enabled, this also refreshes the matching
local DayZ client `!Workshop/<mod_folder>` launcher entry.

```bash
modctl deploy bosssignal
modctl deploy markscontent
```

Requires `modctl build <mod>` to have run first.

#### `modctl ship <mod>`
Full build + deploy cycle.

```bash
modctl ship bosssignal
modctl ship markscontent
```

### Dev loop (Plan 2)

#### `modctl serve`
Start local DayZ Server with all deployed mods + required dependencies (CF).

```bash
modctl serve                   # foreground - stdout streams
modctl serve --detached        # fork background, returns immediately
```

Writes the server PID to `.modctl/state.json` so `restart` can find it.

#### `modctl restart`
Graceful stop of the running server (by PID from state) + start fresh.

```bash
modctl restart
```

#### `modctl tail`
Locate the most recent RPT log under `<dayz_server_path>/profiles/`.

```bash
modctl tail                    # prints path (streaming mode upcoming)
```

#### `modctl watch <mod>`
File-system watcher on the mod's source tree. Any save to a matched file
(default: `*.c` / `config.cpp`) debounced 500ms -> auto-ship.

```bash
modctl watch bosssignal        # blocks until Ctrl+C
```

Combined with `modctl serve --detached`, this is the full fast-iteration loop:
save .c -> rebuild + redeploy in <20s -> server picks up on next restart.

### Diagnosis (Plan 3)

#### `modctl diagnose`
Parse the latest RPT log against modctl's rule library. Surfaces known
Enforce / DayZ Server error patterns with suggested fixes.

```bash
modctl diagnose                 # scans newest RPT in profile dir
modctl diagnose --rpt path.RPT  # explicit file
modctl --json diagnose          # structured output
```

Rule library lives at `tools/modctl/modctl/rules/enforce.yaml`. Contains
10 seed rules covering: null identity deref, backend connection refused,
signing key missing, Enforce compile failure, undefined function, missing
semicolon, FATAL mission shutdown, missing mod dependency, class-override
collision, malformed JSON file. Easy to add more - just append to the yaml.

#### `modctl fix`
Runs `diagnose`, then prompts + applies shell-action fixes one at a time.
Template-only fixes (manual-edit instructions) are surfaced but not applied.

```bash
modctl fix                      # interactive
modctl fix --auto-apply         # apply can_auto_fix rules without prompting
modctl fix --rpt path.RPT       # diagnose a specific RPT file
```

## Global flags

- `--config PATH` / `-c PATH` - point at a different `mods.yaml` (default: `tools/modctl/mods.yaml`)
- `--json` - emit structured JSON output

## Configuration

Every mod is declared in `tools/modctl/mods.yaml`. See that file for the
schema. Secrets (e.g. `SHARED_SECRET`) are referenced via `${ENV_VAR}`
and resolved from the environment at load time.

**Plan 2 added the `dayz_server_*` defaults:**
```yaml
defaults:
  dayz_server_exe: "DayZServer_x64.exe"
  dayz_server_config: "serverDZ.cfg"
  dayz_server_port: 2302
  dayz_server_profile_dir: "profiles"
  dayz_server_startup_params: []
```

Local client Workshop deployment is controlled by:
```yaml
defaults:
  dayz_client_path: "C:/Program Files (x86)/Steam/steamapps/common/DayZ"
  deploy_client_workshop: true
```

## Exit codes

| Code | Category |
|---|---|
| 0 | success |
| 10 | CONFIG_ERROR |
| 20 | BUILD_ERROR |
| 21 | SIGN_ERROR |
| 30 | DEPLOY_ERROR |
| 40 | SERVER_ERROR |
| 50 | TEST_ERROR |
| 60 | IO_ERROR |
| 70 | DEPENDENCY_ERROR |
| 80 | CONFLICT_ERROR |
| 90 | UNKNOWN |

Scripts + Claude Code can reason about failure type without parsing stdout.

## Testing

```bash
pytest -v
```

81 tests cover config loading, error categories, output formatting,
subprocess runner, AddonBuilder wrapper, filesystem helpers, DayZ Server
wrapper, file watcher, diagnosis rule library, and every orchestration module.

## What's next

- **Plan 4** (release / catalog / docs) - shop-ready catalog + release pipeline
- **Plan 5+** - in-game mapping (types.xml / events.xml tuning), server management stack
- LLM-assisted diagnosis for unmatched rule patterns (future layer atop the rule library)

See the design spec for the full roadmap.
