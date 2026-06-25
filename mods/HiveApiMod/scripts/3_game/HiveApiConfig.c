// HiveAPI Configuration
// Edit these values to connect your DayZ server to HiveAPI backend

class HiveApiConfig
{
    // REQUIRED: Change these for your server
    static string API_URL = "http://127.0.0.1:6701";

    // All servers in the same cluster share character data.
    // Replace with the cluster UUID from your backend seed/bootstrap output.
    static string CLUSTER_ID = "00000000-0000-0000-0000-000000000000";

    // Unique for THIS specific server.
    // Replace with the server UUID from your backend seed/bootstrap output.
    static string SERVER_ID = "11111111-1111-1111-1111-111111111111";

    // OPTIONAL: Feature toggles
    static bool ENABLE_AUTO_SAVE = true;
    static bool ENABLE_CROSS_SERVER = true;
    static int SAVE_INTERVAL_SECONDS = 300;
    static bool DEBUG_LOGGING = false;

    // ADVANCED: Network settings
    static int REQUEST_TIMEOUT_MS = 5000;
    static int MAX_RETRIES = 3;
    static int RETRY_DELAY_MS = 1000;

    // Internal - do not change
    static string s_serverToken = "";

    static void LoadFromProfile()
    {
        string path = "$profile:hiveapi_config.json";
        if (!FileExist(path))
        {
            DebugLog("No profile config found at " + path);
            return;
        }

        HiveApiConfigData data = new HiveApiConfigData();
        JsonFileLoader<HiveApiConfigData>.JsonLoadFile(path, data);

        if (data.API_URL != "")
        {
            API_URL = data.API_URL;
        }

        if (data.CLUSTER_ID != "")
        {
            CLUSTER_ID = data.CLUSTER_ID;
        }

        if (data.SERVER_ID != "")
        {
            SERVER_ID = data.SERVER_ID;
        }
    }

    static bool IsConfigured()
    {
        LoadFromProfile();

        if (API_URL == "" || API_URL == "http://localhost:6701")
        {
            Print("[HiveAPI] WARNING: API_URL not configured!");
            return false;
        }

        if (CLUSTER_ID == "")
        {
            Print("[HiveAPI] WARNING: CLUSTER_ID not configured!");
            return false;
        }

        if (SERVER_ID == "")
        {
            Print("[HiveAPI] WARNING: SERVER_ID not configured!");
            return false;
        }

        return true;
    }

    static string GetEndpoint(string path)
    {
        return API_URL + path;
    }

    static void DebugLog(string message)
    {
        if (DEBUG_LOGGING)
        {
            Print("[HiveAPI DEBUG] " + message);
        }
    }
};

class HiveApiConfigData
{
    string API_URL;
    string CLUSTER_ID;
    string SERVER_ID;
};
