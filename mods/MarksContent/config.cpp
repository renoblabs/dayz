// ============================================================
// MarksContent - first content mod.
// Includes: a custom zombie ("Beta Zombie") and a custom
// t-shirt ("BossSignal Beta Tester Shirt"). Pure config-only,
// no scripts, no models - inheritance from base game classes.
// ============================================================

class CfgPatches {
    class MarksContent {
        units[] = {
            "ZmbM_MarksTester"
        };
        weapons[] = {
            "Mark_BetaTester_Shirt",
            "Mark_DebugRifle",
            "Mark_DebugShotgun",
            "Mark_DebugSniper"
        };
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Data", "DZ_Characters", "DZ_AI", "DZ_Weapons_Firearms"};
    };
};

// Register as a CfgMods entry so it shows up in BossSignal's loaded-mods
// enumeration (g_Game.ConfigGetChildName("CfgMods", ...)). Pure-content
// mods don't strictly need this, but without it the dashboard's Loaded
// Mods card silently omits MarksContent.
class CfgMods {
    class MarksContent {
        dir       = "MarksContent";
        name      = "MarksContent";
        author    = "the developer";
        type      = "mod";
        hideName  = 1;
        hidePicture = 1;
    };
};

class CfgVehicles {
    // --- Custom T-Shirt ---------------------------------------------------------------------------------------------------------------------------------
    // Cloned from vanilla TShirt_White; same model + texture, just
    // a different identity + flavor text.
    class TShirt_White;
    class Mark_BetaTester_Shirt : TShirt_White {
        scope = 2;
        displayName = "BossSignal Beta Tester Shirt";
        descriptionShort = "Worn during a 9-hour debug session. Smells faintly of redbull.";
        weight = 200;
    };

    // --- Custom Zombie ----------------------------------------------------------------------------------------------------------------------------------
    // Cloned from ZombieBase (the abstract DayZ infected class - confirmed
    // exists via CF). Registered with BossSignalAPI in BossSignalMission.c
    // so killing one fires a real boss.killed event end-to-end.
    class ZombieBase;
    class ZmbM_MarksTester : ZombieBase {
        scope = 2;
        displayName = "Beta Zombie";
        descriptionShort = "A test infected wearing the BossSignal beta tester shirt.";
    };

    // --- Debug Weapons ----------------------------------------------------------------------------------------------------------------------------------
    // Inherits from vanilla classes; overrides nothing fancy yet, just
    // identity + display.
    class M4A1;
    class Mark_DebugRifle : M4A1 {
        scope = 2;
        displayName = "Debug Rifle";
        descriptionShort = "Field-tested through 11 hours of debugging.";
    };

    class Saiga;
    class Mark_DebugShotgun : Saiga {
        scope = 2;
        displayName = "Debug Shotgun";
        descriptionShort = "For when one shot really should be enough.";
    };

    class Mosin9130;
    class Mark_DebugSniper : Mosin9130 {
        scope = 2;
        displayName = "Debug Sniper";
        descriptionShort = "Adjusted for headshots from across Cherno.";
    };
};
