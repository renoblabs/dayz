// HiveAPI Client - REST API wrapper for DayZ Enforce
// Handles all communication with HiveAPI backend

class HiveApiClient
{
    // ==========================================
    // Server Authentication
    // ==========================================

    // Call this when server starts
    static void ServerLogin(string serverID)
    {
        HiveApiConfig.DebugLog("ServerLogin called for: " + serverID);

        string url = HiveApiConfig.GetEndpoint("/v1/auth/server-login");

        // Build request body
        string requestBody = string.Format("{\"server_id\":\"%1\"}", serverID);

        // Create REST callback
        HiveServerLoginCallback loginCb = new HiveServerLoginCallback(serverID);

        // Send request
        RestContext ctx = GetRestApi().GetRestContext(url);
        if (ctx)
        {
            ctx.SetHeader("application/json");
            ctx.POST(loginCb, "", requestBody);
        }

        Print("[HiveAPI] Authenticating server: " + serverID);
    }

    // ==========================================
    // Character Management
    // ==========================================

    // Claim or create character for a player
    static void ClaimCharacter(string steamID, string clusterID, string serverID, vector position = "0 0 0")
    {
        HiveApiConfig.DebugLog("ClaimCharacter for Steam:" + steamID);

        string url = HiveApiConfig.GetEndpoint("/v1/characters/claim");

        // Build request body
        string requestBody = string.Format("{\"platform_uid\":\"steam:%1\",\"cluster_id\":\"%2\",\"server_id\":\"%3\",\"position\":{\"x\":%4,\"y\":%5,\"z\":%6}}", steamID, clusterID, serverID, position[0].ToString(), position[1].ToString(), position[2].ToString());

        // Create callback
        HiveClaimCharacterCallback cb = new HiveClaimCharacterCallback(steamID);

        // Send request with auth
        RestContext ctx = GetRestApi().GetRestContext(url);
        if (ctx)
        {
            ctx.SetHeader("application/json");
            ctx.POST(cb, "", requestBody);
        }

        Print("[HiveAPI] Claiming character for Steam:" + steamID);
    }

    // ==========================================
    // Inventory Sync
    // ==========================================

    // Save player inventory to HiveAPI
    static void SaveInventory(string characterID, string serverID, map<string, ref InventorySlot> inventory)
    {
        HiveApiConfig.DebugLog("SaveInventory for character: " + characterID);

        string url = HiveApiConfig.GetEndpoint("/v1/inventory/set");

        // Build slots JSON
        string slotsJson = "{";
        int slotCount = 0;

        foreach (string slotKey, InventorySlot slot : inventory)
        {
            if (slotCount > 0) slotsJson += ",";
            slotsJson += string.Format("\"%1\":{\"item\":\"%2\",\"quantity\":%3}", slotKey, slot.item, slot.quantity.ToString());
            slotCount++;
        }

        slotsJson += "}";

        // Build request body
        string requestBody = string.Format("{\"character_id\":\"%1\",\"server_id\":\"%2\",\"slots\":%3}", characterID, serverID, slotsJson);

        // Create callback
        HiveSaveInventoryCallback cb = new HiveSaveInventoryCallback(characterID);

        // Send request
        RestContext ctx = GetRestApi().GetRestContext(url);
        if (ctx)
        {
            ctx.SetHeader("application/json");
            ctx.POST(cb, "", requestBody);
        }

        Print("[HiveAPI] Saving inventory for character: " + characterID);
    }


    // ==========================================
    // Character Heartbeat (position/stats update)
    // ==========================================

    static void SendHeartbeat(string characterID, string serverID, vector position, map<string, float> stats)
    {
        HiveApiConfig.DebugLog("SendHeartbeat for character: " + characterID);

        string url = HiveApiConfig.GetEndpoint("/v1/characters/heartbeat");

        // Build stats JSON
        string statsJson = "{";
        int statCount = 0;

        foreach (string statKey, float statValue : stats)
        {
            if (statCount > 0) statsJson += ",";
            statsJson += string.Format("\"%1\":%2", statKey, statValue.ToString());
            statCount++;
        }

        statsJson += "}";

        // Build request body
        string requestBody = string.Format("{\"character_id\":\"%1\",\"server_id\":\"%2\",\"position\":{\"x\":%3,\"y\":%4,\"z\":%5},\"stats\":%6}", characterID, serverID, position[0].ToString(), position[1].ToString(), position[2].ToString(), statsJson);

        // Create callback
        HiveHeartbeatCallback cb = new HiveHeartbeatCallback();

        // Send request
        RestContext ctx = GetRestApi().GetRestContext(url);
        if (ctx)
        {
            ctx.SetHeader("application/json");
            ctx.POST(cb, "", requestBody);
        }
    }
};


// ==========================================
// Helper Classes
// ==========================================

// Simple inventory slot data
class InventorySlot
{
    string item;
    int quantity;

    void InventorySlot(string itemName, int qty)
    {
        item = itemName;
        quantity = qty;
    }
};

class HiveServerLoginCallback : RestCallback
{
    string m_ServerId;
    
    void HiveServerLoginCallback(string serverId)
    {
        m_ServerId = serverId;
    }
    
    override void OnSuccess(string data, int dataSize)
    {
        HiveApiConfig.DebugLog("Server login response: " + data);

        int tokenStart = data.IndexOf("\"access_token\":\"");
        if (tokenStart != -1)
        {
            tokenStart += 16;
            string afterToken = data.Substring(tokenStart, data.Length() - tokenStart);
            int relTokenEnd = afterToken.IndexOf("\"");
            if (relTokenEnd != -1)
            {
                string token = data.Substring(tokenStart, relTokenEnd);
                HiveApiConfig.s_serverToken = token;
                Print("[HiveAPI] [OK] Server authenticated successfully");
                return;
            }
        }
        Print("[HiveAPI] [FAIL] Failed to parse server token");
    }
    
    override void OnError(int errorCode)
    {
        Print("[HiveAPI] [FAIL] Server login failed: HTTP " + errorCode);
    }
    
    override void OnTimeout()
    {
        Print("[HiveAPI] [FAIL] Server login timeout");
    }
};

class HiveClaimCharacterCallback : RestCallback
{
    string m_SteamId;
    
    void HiveClaimCharacterCallback(string steamId)
    {
        m_SteamId = steamId;
    }
    
    override void OnSuccess(string data, int dataSize)
    {
        HiveApiConfig.DebugLog("Character claim response: " + data);

        int idStart = data.IndexOf("\"character_id\":\"");
        if (idStart != -1)
        {
            idStart += 16;
            string afterId = data.Substring(idStart, data.Length() - idStart);
            int relIdEnd = afterId.IndexOf("\"");
            if (relIdEnd != -1)
            {
                string characterID = data.Substring(idStart, relIdEnd);
                Print("[HiveAPI] [OK] Character claimed: " + characterID);
                
                // Note: MissionServer is in 5_mission, can't be referenced here in 4_world.
                // We just log it for now. The CharacterSync should handle it via a different mechanism if needed.
                return;
            }
        }
        Print("[HiveAPI] [FAIL] Failed to parse character ID");
    }
    
    override void OnError(int errorCode)
    {
        Print("[HiveAPI] [FAIL] Character claim failed: HTTP " + errorCode);
    }
    
    override void OnTimeout()
    {
        Print("[HiveAPI] [FAIL] Character claim timeout");
    }
};

class HiveSaveInventoryCallback : RestCallback
{
    string m_CharacterId;
    
    void HiveSaveInventoryCallback(string characterId)
    {
        m_CharacterId = characterId;
    }
    
    override void OnSuccess(string data, int dataSize)
    {
        HiveApiConfig.DebugLog("Inventory save response: " + data);
        Print("[HiveAPI] [OK] Inventory saved successfully");
    }
    
    override void OnError(int errorCode)
    {
        Print("[HiveAPI] [FAIL] Inventory save failed: HTTP " + errorCode);
    }
    
    override void OnTimeout()
    {
        Print("[HiveAPI] [FAIL] Inventory save timeout");
    }
};

class HiveHeartbeatCallback : RestCallback
{
    override void OnSuccess(string data, int dataSize)
    {
        HiveApiConfig.DebugLog("Heartbeat success");
    }
    
    override void OnError(int errorCode)
    {
        HiveApiConfig.DebugLog("Heartbeat error: HTTP " + errorCode);
    }
    
    override void OnTimeout()
    {
        HiveApiConfig.DebugLog("Heartbeat timeout");
    }
};
