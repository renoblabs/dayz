// ============================================================
// @TestHarness - dev-only scripted-scenario runner for BossSignal
//                / TrophyHunter end-to-end validation.
//
// LOAD ORDER: after @CommunityFramework, @BossSignal, @TrophyHunter.
// ONLY load in dev. NEVER distribute to production/customer servers.
//
// Activation: set `testMode = 1;` in your serverDZ.cfg OR pass
//   `-testMode=1` on the DayZ Server command line. The mod stays
//   inert unless that flag is set.
// ============================================================

class CfgPatches {
    class TestHarness {
        units[]          = {};
        weapons[]        = {};
        requiredVersion  = 0.1;
        requiredAddons[] = {"Community_Framework", "BossSignal"};
    };
};

class CfgMods {
    class TestHarness {
        type         = "mod";
        author       = "modctl";
        name         = "TestHarness - modctl dev-only scenario runner";
        version      = "0.1.0";
        dependencies[] = {"Community_Framework", "BossSignal", "Mission"};

        class defs {
            class gameScriptModule {
                value   = "";
                files[] = {"TestHarness/scripts/3_game"};
            };
            class missionScriptModule {
                value   = "";
                files[] = {"TestHarness/scripts/5_mission"};
            };
        };
    };
};
