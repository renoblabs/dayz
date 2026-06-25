// ============================================================

// BossSignalConfig - static configuration class

// Load order : 3_game  (available on client + server, but only

//              relevant on the server side - REST calls are gated)

//

// Config can be overridden at runtime from a JSON file in the profile dir

// via JsonFileLoader<BossSignalConfigData>.JsonLoadFile(path); see LoadFromProfile().

// ============================================================



// ?? Edit these before deploying ?????????????????????????????

// If you're running the backend locally:  http://localhost:8080

// If you're running it on a VPS:         https://yourdomain.com:8080

// ????????????????????????????????????????????????????????????

class BossSignalConfig {

    // Where the BossSignal backend is listening

    static string BACKEND_URL     = "http://127.0.0.1:6700";



    // Shared secret - must match BOSSSIGNAL_SECRET in backend .env

    // Placeholder only. Set this to a random value before deploying
    // (e.g. openssl rand -hex 32) and configure the same value as
    // BOSSSIGNAL_SECRET on the backend. The backend should refuse requests
    // if its secret is left unset, so never ship with CHANGE_ME in production.

    static string SHARED_SECRET   = "CHANGE_ME";



    // Identifies this server in the dashboard.

    // Match this to what you call the server in your CFTools/Battlemetrics setup.

    static string SERVER_ID       = "server_01";



    // Mod version - do not edit, used for compatibility handshakes

    static string VERSION         = "0.1.0";



    // How often to push a heartbeat (seconds).

    // Heartbeats report player count + active boss list even when nothing dies.

    static float HEARTBEAT_INTERVAL = 60.0;



    // Set true to emit per-hit damage events (PLAYER_BOSS_DAMAGE).

    // Noisy - enable only if your dashboard uses it.

    static bool EMIT_DAMAGE_EVENTS = false;



    // Verbose RPT logging. Set false on production servers.

    static bool DEBUG_LOGGING     = false;



    // Dev-only: fire a synthetic boss encounter 30s after OnInit so the
    // full mod -> backend event path can be validated without a real boss
    // mod or player-driven kill. Keep false on production servers.

    static bool DEV_SYNTHETIC_ENCOUNTER = false;



    // ?? Internal helpers ?????????????????????????????????????



    static void LoadFromProfile() {
        string path = "$profile:bosssignal_config.json";
        if (FileExist(path)) {
            BossSignalConfigData data = new BossSignalConfigData();
            JsonFileLoader<BossSignalConfigData>.JsonLoadFile(path, data);
            
            if (data.SERVER_ID != "") {
                SERVER_ID = data.SERVER_ID;
                BossSignalConfig.Log("Loaded SERVER_ID from profile: " + SERVER_ID);
            }
            if (data.BACKEND_URL != "") {
                BACKEND_URL = data.BACKEND_URL;
                BossSignalConfig.Log("Loaded BACKEND_URL from profile: " + BACKEND_URL);
            }
        } else {
            BossSignalConfig.Log("No config found at " + path + ", using defaults.");
        }
    }

    static void Load() {
        // Legacy load method
        LoadFromProfile();
        BossSignalConfig.Log("Config loaded | Server=" + SERVER_ID + " | URL=" + BACKEND_URL + " | v" + VERSION);
    }



    static void Log(string msg) {

        if (BossSignalConfig.DEBUG_LOGGING) {

            Print("[BossSignal] " + msg);

        }

    }



    static void Warn(string msg) {

        Print("[BossSignal][WARN] " + msg);

    }



    static void Err(string msg) {

        Print("[BossSignal][ERROR] " + msg);

    }



    // File-based trace - writes to $profile:bs_trace.txt so we can see

    // boot-time execution even when RPT is buffered. Each call appends

    // the tag on a new line. Safe no-op if filesystem is unreachable.

    static void Trace(string tag) {

        FileHandle fh = OpenFile("$profile:bs_trace.txt", FileMode.APPEND);

        if (fh != 0) {

            FPrintln(fh, tag);

            CloseFile(fh);

        }

    }
};

class BossSignalConfigData {
    string SERVER_ID;
    string BACKEND_URL;
}

