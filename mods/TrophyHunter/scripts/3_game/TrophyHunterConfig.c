// ============================================================
// TrophyHunterConfig - static configuration class (load order 3_game).
// Mirror of BossSignalConfig - same shared-secret header convention.
// ============================================================

class TrophyHunterConfig {
    static string BACKEND_URL   = "http://127.0.0.1:6700";
    // Placeholder only. Set this to a random value before deploying and match it
    // to BOSSSIGNAL_SECRET on the backend. The backend should refuse requests if
    // its secret is unset, so never ship with CHANGE_ME in production.
    static string SHARED_SECRET = "CHANGE_ME";
    static string SERVER_ID     = "server_01";
    static string VERSION       = "0.1.0";

    // Grace period (seconds) during which a trophy cannot be looted from a corpse.
    static int  GRACE_SECONDS   = 600;

    // Verbose RPT logging. Keep false on production servers.
    static bool DEBUG_LOGGING   = false;

    static string BOSSES_JSON_PATH = "$mission:TrophyHunter/bosses.json";

    static void LoadFromProfile() {
        string path = "$profile:trophyhunter_config.json";
        if (FileExist(path)) {
            TrophyHunterConfigData data = new TrophyHunterConfigData();
            JsonFileLoader<TrophyHunterConfigData>.JsonLoadFile(path, data);

            if (data.SERVER_ID != "") {
                SERVER_ID = data.SERVER_ID;
                TrophyHunterConfig.Log("Loaded SERVER_ID from profile: " + SERVER_ID);
            }
            if (data.BACKEND_URL != "") {
                BACKEND_URL = data.BACKEND_URL;
                TrophyHunterConfig.Log("Loaded BACKEND_URL from profile: " + BACKEND_URL);
            }
            if (data.SHARED_SECRET != "") {
                SHARED_SECRET = data.SHARED_SECRET;
                TrophyHunterConfig.Log("Loaded SHARED_SECRET from profile.");
            }
        } else {
            TrophyHunterConfig.Log("No config found at " + path + ", using defaults.");
        }
    }

    static void Load() {
        LoadFromProfile();
        TrophyHunterConfig.Log("Config loaded | Server=" + SERVER_ID + " | URL=" + BACKEND_URL + " | v" + VERSION);
    }

    static void Log(string msg)  { if (TrophyHunterConfig.DEBUG_LOGGING) Print("[TrophyHunter] " + msg); }
    static void Warn(string msg) { Print("[TrophyHunter][WARN] "  + msg); }
    static void Err(string msg)  { Print("[TrophyHunter][ERROR] " + msg); }
};

class TrophyHunterConfigData {
    string SERVER_ID;
    string BACKEND_URL;
    string SHARED_SECRET;
};
