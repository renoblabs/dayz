// ============================================================
// BossSignal - DayZ boss-encounter telemetry mod
// Version : 0.1.0-alpha
// Requires: Community Framework (CF)
//
// Drop @BossSignal/ into your server mods folder.
// Set BACKEND_URL + SHARED_SECRET in BossSignalConfig.c
// (or wait for v0.2 which reads bosssignal.json from profile dir).
//
// From your own boss mod - one call to hook in:
//   BossSignalAPI.RegisterBossClass("YourBossClass", "The Warlord");
//   BossSignalAPI.EmitBossSpawned(myBossEntity, "YourBossClass");
// BossSignal handles kill tracking, participant damage, and HTTP emit.
// ============================================================

class CfgPatches {
    class BossSignal {
        units[]          = {};
        weapons[]        = {};
        requiredVersion  = 0.1;
        requiredAddons[] = {"Community_Framework"};
    };
};

class CfgMods {
    class BossSignal {
        dir          = "BossSignal";
        picture      = "";
        action       = "";
        hideName     = 1;
        hidePicture  = 1;
        name         = "BossSignal - Boss Encounter Telemetry";
        credits      = "";
        author       = "BossSignal";
        authorID     = "0";
        version      = "0.1.0";
        extra        = 0;
        type         = "mod";
        dependencies[] = {"Game", "World", "Mission"};
        class defs {
            class gameScriptModule {
                value    = "";
                files[]  = {"BossSignal/scripts/3_game"};
            };
            class worldScriptModule {
                value    = "";
                files[]  = {"BossSignal/scripts/4_world"};
            };
            class missionScriptModule {
                value    = "";
                files[]  = {"BossSignal/scripts/5_mission"};
            };
        };
    };
};
