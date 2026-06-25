// ============================================================
// TrophyHunter - DayZ boss-trophy award mod
// Version : 0.1.0-alpha
// Requires: Community Framework (CF), BossSignal
//
// Drop @TrophyHunter/ into your server mods folder AFTER @BossSignal.
// Edit trophyhunter-mod/config/bosses.json to map boss class names
// to trophy item classes.
// ============================================================

class CfgPatches {
    class TrophyHunter {
        units[]          = {};
        weapons[]        = {};
        requiredVersion  = 0.1;
        requiredAddons[] = {"Community_Framework", "BossSignal"};
    };
};

class CfgMods {
    class TrophyHunter {
        type         = "mod";
        author       = "TrophyHunter";
        name         = "TrophyHunter - Boss Kill Trophy System";
        version      = "0.1.0";
        dependencies[] = {"Community_Framework", "BossSignal", "Mission"};

        class defs {
            class gameScriptModule {
                value   = "";
                files[] = {"TrophyHunter/scripts/3_game"};
            };
            class worldScriptModule {
                value   = "";
                files[] = {"TrophyHunter/scripts/4_world"};
            };
            class missionScriptModule {
                value   = "";
                files[] = {"TrophyHunter/scripts/5_mission"};
            };
        };
    };
};

class CfgVehicles {
    // Trophies - reskins of existing DayZ items for MVP.
    // Each maps to a boss class in config/bosses.json.

    class Inventory_Base;

    class WarlordsCrown : Inventory_Base {
        scope = 2;
        displayName = "Warlord's Crown";
        descriptionShort = "A bloodied iron crown, torn from the Warlord's head.";
        model = "\dz\gear\cooking\sharpeningstone.p3d";
        weight = 800;
        itemSize[] = {1,1};
        inventorySlot[] = {"Armband"};
        varQuantityInit = 1;
        varQuantityMin = 0;
        varQuantityMax = 1;
    };

    class AbominationsJaw : Inventory_Base {
        scope = 2;
        displayName = "Abomination's Jaw";
        descriptionShort = "The oversized jawbone of the Abomination.";
        model = "\dz\gear\cooking\sharpeningstone.p3d";
        weight = 1200;
        itemSize[] = {2,1};
        inventorySlot[] = {"Armband"};
        varQuantityInit = 1;
        varQuantityMin = 0;
        varQuantityMax = 1;
    };

    class HeavyTankPlate : Inventory_Base {
        scope = 2;
        displayName = "Heavy Tank Plate";
        descriptionShort = "A dense armor plate from the Tank boss.";
        model = "\dz\gear\cooking\sharpeningstone.p3d";
        weight = 3500;
        itemSize[] = {2,2};
        inventorySlot[] = {"Body"};
        varQuantityInit = 1;
        varQuantityMin = 0;
        varQuantityMax = 1;
    };

    class NecromancersSkull : Inventory_Base {
        scope = 2;
        displayName = "Necromancer's Skull";
        descriptionShort = "A glowing skull taken from the Necromancer.";
        model = "\dz\gear\cooking\sharpeningstone.p3d";
        weight = 600;
        itemSize[] = {1,1};
        inventorySlot[] = {"Armband"};
        varQuantityInit = 1;
        varQuantityMin = 0;
        varQuantityMax = 1;
    };

    class HuntersFang : Inventory_Base {
        scope = 2;
        displayName = "Hunter's Fang";
        descriptionShort = "A pendant carved from the Hunter Elite's claw.";
        model = "\dz\gear\cooking\sharpeningstone.p3d";
        weight = 100;
        itemSize[] = {1,1};
        inventorySlot[] = {"Armband"};
        varQuantityInit = 1;
        varQuantityMin = 0;
        varQuantityMax = 1;
    };
};
