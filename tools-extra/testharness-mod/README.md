# @TestHarness - modctl dev-only scenario runner

Scripted end-to-end validation for BossSignal + TrophyHunter. Fires named
scenarios on a timer when the DayZ Server is started with `testMode=1`.

**Never distribute this mod to customer servers.** Dev-only, local validation.

## How it's activated

Either:

1. `serverDZ.cfg` - add the line:
   ```
   testMode = 1;
   ```

2. Or pass `-testMode=1` on the DayZ Server command line.

Absent that, the mod loads but stays inert.

## Current scenarios

| Scenario | Purpose |
|---|---|
| `boss_spawn_then_despawn` | Placeholder, will spawn a test boss, wait, despawn it. Substitute the boss classnames from your own or a licensed external boss-content mod. |
| `bosssignal_emit_event` | Placeholder - will fire a test event through the BossSignal emitter once its API stabilises post-first-compile. |

Both currently log and pass. They become real once we have the actual
boss class names + a stable BossSignal emitter API (post-validation sprint).

## Result file

After scenarios run, TestRunner writes:

```
$profile:testharness_results.json
```

(Which resolves to something like `C:\Users\<user>\...\DayZServer\profiles\testharness_results.json`.)

Format:
```json
{
  "results": [
    {"scenario": "boss_spawn_then_despawn", "status": "PASS"},
    {"scenario": "bosssignal_emit_event", "status": "PASS"}
  ]
}
```

modctl's test orchestration reads this file back to report pass/fail.

## Adding a new scenario

1. Add name to `TestHarnessConfig.SCENARIOS`
2. Add a matching `bool Scenario_YourName()` method on `TestRunner`
3. Wire it into the `switch` in `RunNextScenario`
4. Rebuild: `modctl build testharness`
5. Redeploy: `modctl deploy testharness`

## Build + deploy via modctl

```bash
modctl build testharness
modctl deploy testharness
modctl serve                   # (add testMode=1 to serverDZ.cfg first)
modctl tail                    # watch the [TestHarness] log lines
```
