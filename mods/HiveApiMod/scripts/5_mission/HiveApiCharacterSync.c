// HiveAPI Character Sync Manager
// Handles automatic character sync on player join/leave

modded class MissionServer
{
    private ref map<string, string> m_playerCharacterMap;  // SteamID -> CharacterID
    private ref map<string, ref Timer> m_autoSaveTimers;

    void MissionServer()
    {
        m_playerCharacterMap = new map<string, string>();
        m_autoSaveTimers = new map<string, ref Timer>();
    }

    // Called when mission starts
    override void OnInit()
    {
        super.OnInit();

        Print("[HiveAPI] Mission server initialized");

        // Check configuration
        if (!HiveApiConfig.IsConfigured())
        {
            Print("[HiveAPI] [ERROR] Configuration incomplete! Edit HiveApiConfig.c");
            Print("[HiveAPI] Required: API_URL, CLUSTER_ID, SERVER_ID");
            return;
        }

        // Authenticate server with HiveAPI AFTER mission load to prevent hang
        GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(HiveApiClient.ServerLogin, 10000, false, HiveApiConfig.SERVER_ID);

        Print("[HiveAPI] Configuration loaded:");
        Print("[HiveAPI]   API URL: " + HiveApiConfig.API_URL);
        Print("[HiveAPI]   Cluster: " + HiveApiConfig.CLUSTER_ID);
        Print("[HiveAPI]   Server: " + HiveApiConfig.SERVER_ID);
    }

    // Called when player connects
    override void InvokeOnConnect(PlayerBase player, PlayerIdentity identity)
    {
        super.InvokeOnConnect(player, identity);

        if (!identity)
            return;

        string steamID = identity.GetPlainId();
        vector spawnPos = player.GetPosition();

        Print("[HiveAPI] Player connecting: Steam:" + steamID);

        // Claim character from HiveAPI. Enforce won't parse multi-line
        // arg lists when the called function has default-valued params,
        // so this is intentionally one line.
        HiveApiClient.ClaimCharacter(steamID, HiveApiConfig.CLUSTER_ID, HiveApiConfig.SERVER_ID, spawnPos);

        // Start auto-save timer if enabled
        if (HiveApiConfig.ENABLE_AUTO_SAVE && HiveApiConfig.SAVE_INTERVAL_SECONDS > 0)
        {
            StartAutoSave(steamID, player);
        }
    }

    // Called when player disconnects
    override void InvokeOnDisconnect(PlayerBase player)
    {
        if (player && player.GetIdentity())
        {
            string steamID = player.GetIdentity().GetPlainId();

            Print("[HiveAPI] Player disconnecting: Steam:" + steamID);

            // Stop auto-save timer
            StopAutoSave(steamID);

            // Save character on disconnect
            if (HiveApiConfig.ENABLE_AUTO_SAVE)
            {
                SavePlayerCharacter(player, steamID);
            }

            // Cleanup
            m_playerCharacterMap.Remove(steamID);
        }

        super.InvokeOnDisconnect(player);
    }

    // Save player character to HiveAPI
    void SavePlayerCharacter(PlayerBase player, string steamID)
    {
        string characterID = GetCharacterID(steamID);

        if (characterID == "")
        {
            HiveApiConfig.DebugLog("No character ID for Steam:" + steamID);
            return;
        }

        // Gather inventory data
        map<string, ref InventorySlot> inventory = new map<string, ref InventorySlot>();
        GatherPlayerInventory(player, inventory);

        // Save to HiveAPI
        HiveApiClient.SaveInventory(characterID, HiveApiConfig.SERVER_ID, inventory);

        // Send heartbeat with position and stats
        map<string, float> stats = new map<string, float>();
        stats.Set("health", player.GetHealth("", "Health"));
        stats.Set("blood", player.GetHealth("", "Blood"));
        // stats.Set("stamina", player.GetStamina());

        HiveApiClient.SendHeartbeat(characterID, HiveApiConfig.SERVER_ID, player.GetPosition(), stats);
    }

    // Gather player inventory into a pre-allocated map.
    void GatherPlayerInventory(PlayerBase player, map<string, ref InventorySlot> inventory)
    {
        int slotIndex = 0;

        // Hands
        EntityAI inHands = player.GetHumanInventory().GetEntityInHands();
        if (inHands)
        {
            inventory.Set(slotIndex.ToString(), new InventorySlot(inHands.GetType(), 1));
            slotIndex++;
        }

        // Clothing slots
        for (int i = 0; i < player.GetInventory().GetAttachmentSlotsCount(); i++)
        {
            EntityAI attachment = player.GetInventory().GetAttachmentFromIndex(i);
            if (attachment)
            {
                inventory.Set(slotIndex.ToString(), new InventorySlot(attachment.GetType(), 1));
                slotIndex++;
            }
        }

        // Cargo items
        array<EntityAI> cargoItems = new array<EntityAI>();
        player.GetInventory().EnumerateInventory(InventoryTraversalType.PREORDER, cargoItems);

        foreach (EntityAI item : cargoItems)
        {
            if (item && item != player)
            {
                inventory.Set(slotIndex.ToString(), new InventorySlot(item.GetType(), 1));
                slotIndex++;
            }
        }

        HiveApiConfig.DebugLog("Gathered " + inventory.Count() + " inventory items");
    }

    // Start periodic auto-save
    void StartAutoSave(string steamID, PlayerBase player)
    {
        HiveApiConfig.DebugLog("Starting auto-save for Steam:" + steamID);

        Timer timer = new Timer();
        // timer.Run(HiveApiConfig.SAVE_INTERVAL_SECONDS, this, "OnAutoSaveTick", new Param2<string, PlayerBase>(steamID, player), true);

        m_autoSaveTimers.Set(steamID, timer);
    }

    // Stop periodic auto-save
    void StopAutoSave(string steamID)
    {
        Timer timer;
        if (m_autoSaveTimers.Find(steamID, timer))
        {
            timer.Stop();
            m_autoSaveTimers.Remove(steamID);
        }
    }

    // Auto-save tick
    void OnAutoSaveTick(string steamID, PlayerBase player)
    {
        if (player && player.IsAlive())
        {
            HiveApiConfig.DebugLog("Auto-save tick for Steam:" + steamID);
            SavePlayerCharacter(player, steamID);
        }
    }

    // Get character ID for steam ID
    string GetCharacterID(string steamID)
    {
        string characterID = "";
        m_playerCharacterMap.Find(steamID, characterID);
        return characterID;
    }

    // Store character ID (call this after receiving ClaimCharacter response)
    void SetCharacterID(string steamID, string characterID)
    {
        m_playerCharacterMap.Set(steamID, characterID);
        Print("[HiveAPI] Character ID stored: " + characterID + " for Steam:" + steamID);
    }
};
