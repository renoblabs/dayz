# TraderPlus Investigation (Phase 1, Session 6)

**Question coming in:** "TraderPlus suspiciously missing from top 30 - must be resolved before any conversation."

## Conclusion

**Not a parser bug, not a data source limitation. TraderPlus genuinely ranks #31 in the populated top-200 sample.** The trader category looks fragmented - and the dominant trader system is bundled with DayZ-Expansion, not a standalone TraderPlus deployment.

## Evidence

### What's actually in the data (2026-04-26 snapshot)

```
raw_mod_string                          | workshop_id | servers
-----------------------------------------+-------------+---------
DayZ-Expansion-Market                    | 2572328470  |      52    ← rank 8 in top 30
TraderPlus                               | 2458896948  |      24    ← rank 31 (just outside top 30)
dayztrader                               | 2054775140  |       9    ← actually Inkota with confusing name
Trader Mod                               | 1590841260  |       7    ← Dr. Jones original Trader
Simple - Trader Signs Series II          | 3025154727  |       1
TraderPlus Car Deploy Fix                | 3148873554  |       1
BetterVendingMachines - EnhancedBanking  |             |       1
ATM Hacking                              |             |       1
AdvancedBanking V2                       |             |       2
Banking                                  |             |       3
```

### What this actually means

The "trader / economy" category breaks down as:
- **52 servers (26%)** running DayZ-Expansion-Market - bundled with Expansion, dominant by far
- **24 servers (12%)** running TraderPlus standalone - second-tier
- **~16 servers (8% combined)** running Dr. Jones's classic Trader Mod
- **~6 servers** running various banking/ATM/vending systems

So **at least 46% of populated top-200 servers run SOME trader/economy system**, but they're spread across at least 3 distinct mod families. The "TraderPlus is dominant" intuition isn't supported by Battlemetrics' deployment data.

### Why the rank-31 number didn't show

Top-30 query `OFFSET 28 LIMIT 12` shows TraderPlus at exactly position #31, just below `BBP` (29) and `Vehicle3PP` (25). Cutoff was arbitrary - TraderPlus is in the top 16% of all deployed mods, just not the top 15.

## Conversational handling

**If TraderPlus comes up:**
> "Yeah, TraderPlus is at rank 31 in our top-200 server sample - about 12%. The actual dominant trader system is Expansion-Market, which comes bundled with Expansion-Core and shows up on 26% of populated servers. The standalone-trader market is split three ways - TraderPlus, Dr Jones's old Trader Mod, and a long tail of banking/ATM stuff."

**If pressed on the methodology:**
> "Battlemetrics is our source for deployment data. They report mod IDs returned by each server's query response, so we can only see what the server announces. There's some mod-ID collision and reuse stuff to be careful of, but TraderPlus's ID (2458896948) is consistent across all 24 servers we see it on, so I trust that count."

**On the common assumption that "everyone runs TraderPlus":**
> "I'd actually expect that's true in certain scenes. Our top 200 is sorted by current player count - heavy PvP and Expansion-bundled servers may dominate that cut. If we sliced by 'PvE servers' or 'small-pop community servers' the trader breakdown probably looks different. Worth investigating."

## Key finding

The trader breakdown is itself a finding - *"the trader category isn't dominated by TraderPlus, it's dominated by Expansion's bundled market system at 2x the deployment"* is a non-obvious data point worth carrying.
