# TrophyHunter - Pre-Deployment Checklist

Everything here blocks real-network deployment but does NOT block local dev.

## 1. Identify the external boss-content mod
- [ ] Obtain the exact Workshop mod name, ID, or server mod list.
- [ ] Find the mod on Steam Workshop and record attribution metadata.
- [ ] Subscribe + let DayZ auto-download. Or unpack the `.pbo` with DayZ Tools.
- [ ] Read the unpacked `config.cpp`; record every boss class name.

## 2. Populate `bosses.json`
- [ ] Replace placeholder class names in `mods/TrophyHunter/config/bosses.json`
      with the external mod's real boss class names.
- [ ] If it has more than 5 boss types, extend `mods/TrophyHunter/config.cpp`
      and dashboard's `TROPHY_DEFS` to match.

## 3. Confirm shared-character hive
- [ ] Check whether the target server network has a shared player-character hive.
- [ ] If not, trophies are server-local for MVP (design spec §2 allows this).

## 4. Confirm damage-tracking compatibility
- [ ] Join a target test server. Watch BossSignal RPT lines.
- [ ] Verify `boss.killed` events record non-empty `participants` arrays.
- [ ] If empty, extend BossSignal's damage tracker (DEVLOG follow-up).

## 5. Sign the PBO
- [ ] Install DayZ Tools from Steam.
- [ ] Run `build-pipeline/sign-keygen.bat` once.
- [ ] Pack/sign/deploy through `tools-extra/modctl`: `python -m modctl -c mods.yaml ship trophyhunter`
- [ ] Never commit `*.biprivatekey`.

## 6. Test server deploy
- [ ] Host a local DayZ server w/ BossSignal + TrophyHunter + a test boss mod.
- [ ] Spawn -> damage -> kill -> verify BossSignal records participants/top-damager, then verify trophy lands + dashboard flashes.
- [ ] Walk DEVLOG-TH-001 through DEVLOG-TH-006.

## 7. Operator deployment
- [ ] Coordinate with the server operator to install and key-whitelist the mod.
