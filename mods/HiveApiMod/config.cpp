class CfgPatches
{
    class HiveApiMod
    {
        units[] = {};
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] =
        {
            "DZ_Data",
            "DZ_Scripts",
            "Community_Framework"
        };
    };
};

class CfgMods
{
    class HiveApiMod
    {
        dir = "HiveApiMod";
        picture = "";
        action = "";
        hideName = 1;
        hidePicture = 1;
        name = "HiveAPI Integration";
        credits = "Your Name";
        author = "Your Name";
        authorID = "0";
        version = "1.0";
        extra = 0;
        type = "mod";

        dependencies[] = {"Game", "World", "Mission"};

        class defs
        {
            class gameScriptModule
            {
                value = "";
                files[] = {"HiveApiMod/scripts/3_game"};
            };
            class worldScriptModule
            {
                value = "";
                files[] = {"HiveApiMod/scripts/4_world"};
            };
            class missionScriptModule
            {
                value = "";
                files[] = {"HiveApiMod/scripts/5_mission"};
            };
        };
    };
};
