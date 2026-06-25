# HiveAPI DayZ Mod Template

**Prototype DayZ mod scaffold for connecting a server to the HiveAPI backend.**

> Current status: this is not a production-ready persistence mod yet. Server login, character claim, heartbeat, and inventory request helpers exist, but mod-side Bearer token use, character-id handoff, restore/save hooks, autosave, and kill-event reporting still need wiring.

---

## 📦 What This Mod Does

This mod currently provides scaffolding for:
- Server authentication with HiveAPI
- Character claim and heartbeat requests
- Inventory apply/set request helpers
- Profile-file configuration for API URL, cluster ID, and server ID

The full join/load, disconnect/save, and cross-server transfer loop is still planned work.

---

## 🚀 Quick Setup

### Step 1: Configure API Connection

Edit `scripts/3_game/HiveApiConfig.c` or provide `$profile:hiveapi_config.json`:

```cpp
static string API_URL = "http://your-api-server:6701";  // Change to your HiveAPI URL
static string CLUSTER_ID = "your-cluster-uuid";         // Get from demo seed output
static string SERVER_ID = "your-server-uuid";           // Get from demo seed output
```

**Where to get IDs:**
- Use the local stack bootstrap/seed flow for `backends/hiveapi`, or call `/v1/server-stub/bootstrap` in a dev environment
- The backend must have matching `Cluster` and `Server` rows before claim/heartbeat calls succeed
- For Docker local stack access from the host, use `http://127.0.0.1:6701`; in-container examples may use port `8000`

### Step 2: Copy Files to Your Mod

```
YourDayZMod/
|-- config.cpp
`-- scripts/
    |-- 3_game/
    |   `-- HiveApiConfig.c          ← Configuration
    |-- 4_world/
    |   `-- HiveApiClient.c          ← API wrapper
    `-- 5_mission/
        `-- HiveApiCharacterSync.c   ← Mission hooks and sync scaffold
```

Copy all files from this directory into your mod.

### Step 3: Build Your Mod

Use DayZ Tools or the repo `modctl` workflow to build the prototype mod. Do not publish or deploy it as a production persistence mod until the token, character-id, restore, autosave, and death/disconnect paths are completed and verified.

### Step 4: Add Mod to Server

**For Server:**
```
-mod=@YourModName;@HiveApiMod
```

**For Client:**
- Subscribe to mod on Steam Workshop
- Enable in DayZ Launcher

---

## 📖 How It Works

### Server Startup
```cpp
// In HiveApiCharacterSync.c
override void OnInit()
{
    super.OnInit();
    // Authenticate server with HiveAPI
    HiveApiClient.ServerLogin(SERVER_ID);
}
```

### Player Joins
```cpp
override void InvokeOnConnect(PlayerBase player, PlayerIdentity identity)
{
    super.InvokeOnConnect(player, identity);
    string steamID = identity.GetPlainId();
    HiveApiClient.ClaimCharacter(steamID, CLUSTER_ID, SERVER_ID, player.GetPosition());
}
```

### Player Disconnects
```cpp
override void InvokeOnDisconnect(PlayerBase player)
{
    // Intended save path. Current code needs character-id handoff before this works.
    SavePlayerCharacter(player, player.GetIdentity().GetPlainId());
    super.InvokeOnDisconnect(player);
}
```

---

## 🔧 Configuration Options

### HiveApiConfig.c

```cpp
class HiveApiConfig
{
    // API Connection
    static string API_URL = "http://127.0.0.1:6701";
    static string CLUSTER_ID = "";
    static string SERVER_ID = "";

    // Settings
    static bool ENABLE_AUTO_SAVE = true;        // Intended save-on-disconnect toggle
    static bool ENABLE_CROSS_SERVER = true;     // Design target, not complete
    static int SAVE_INTERVAL_SECONDS = 300;     // Autosave interval; timer is currently disabled in code
    static bool DEBUG_LOGGING = false;         // Verbose logs

    // Timeouts
    static int REQUEST_TIMEOUT_MS = 5000;      // API request timeout
    static int MAX_RETRIES = 3;                // Retry failed requests
};
```

---

## 🎮 Testing the Mod

### 1. Start Backend
```bash
cd backends/hiveapi/ops
docker compose up -d --build
```

### 2. Verify Backend Running
```bash
curl http://localhost:6701/health
```

### 3. Create Test Data
```bash
cd backends/hiveapi
# Use the repo seed/bootstrap flow or POST /v1/server-stub/bootstrap in dev
```

Copy the server UUID from output.

### 4. Update Mod Config
Edit `HiveApiConfig.c` or `$profile:hiveapi_config.json` with the server UUID from step 3.

### 5. Launch DayZ Server with Mod
```
DayZServer_x64.exe -config=serverDZ.cfg -port=2302 -mod=@HiveApiMod
```

### 6. Join Server and Test
- Join your server
- Check server logs for: `[HiveAPI] Server authenticated successfully`
- Check character claim: `[HiveAPI] [OK] Character claimed: <CharacterID>`. The ID is logged but not yet handed back into the sync map.

---

## 📊 Monitoring

### View Server Logs
Watch for HiveAPI messages:
```
[HiveAPI] Server authenticated successfully
[HiveAPI] Character claimed for Steam:76561198XXXXXXXX
[HiveAPI] Inventory saved for character abc-123   # only after character-id handoff is wired
```

### Check Backend Logs
```bash
cd backends/hiveapi/ops
docker compose logs -f api
```

### View Events in Dashboard
```bash
Use `GET /v1/admin/events` or `/v1/admin/events/stream` on the HiveAPI backend. The React dashboard in `frontends/web-ui` is primarily the BossSignal operator dashboard, not a completed Hive persistence UI.
```

---

## 🔍 API Methods Available

### HiveApiClient Methods

```cpp
// Server authentication (call on startup)
static void ServerLogin(string serverID);

// Character management
static void ClaimCharacter(string steamID, string clusterID, string serverID);
static void SendHeartbeat(string characterID, string serverID, vector position, map<string, float> stats);

// Inventory sync
static void SaveInventory(string characterID, string serverID, map<string, ref InventorySlot> inventory);
```

### Example Usage

```cpp
// In your GameMode or MissionServer:

// When server starts
override void OnInit()
{
    super.OnInit();
    HiveApiClient.ServerLogin(HiveApiConfig.SERVER_ID);
}

// When player joins
override void InvokeOnConnect(PlayerBase player, PlayerIdentity identity)
{
    super.InvokeOnConnect(player, identity);

    string steamID = identity.GetPlainId();
    HiveApiClient.ClaimCharacter(
        steamID,
        HiveApiConfig.CLUSTER_ID,
        HiveApiConfig.SERVER_ID
    );
}

// When player leaves
override void InvokeOnDisconnect(PlayerBase player)
{
    // Current scaffold needs the claimed character ID to be stored before this works.
    SavePlayerCharacter(player, player.GetIdentity().GetPlainId());

    super.InvokeOnDisconnect(player);
}
```

---

## 🐛 Troubleshooting

### Mod not connecting to API

**Check:**
1. API URL is correct in `HiveApiConfig.c`
2. Backend is running: `curl http://your-api:6701/health` for the local host-mapped stack, or port `8000` inside the compose network
3. Firewall allows the host-mapped API port
4. Server logs show connection errors

**Fix:**
```cpp
// Enable debug logging
static bool DEBUG_LOGGING = true;
```

### Characters not syncing

**Check:**
1. Server authenticated successfully (check logs)
2. Cluster ID and Server ID are valid UUIDs
3. Backend has matching cluster/server rows: `curl http://your-api:6701/v1/admin/overview`

**Fix:**
```bash
# Use /v1/server-stub/bootstrap or seed matching Cluster/Server rows
cd backends/hiveapi
```

### Inventory not saving

**Check:**
1. `ENABLE_AUTO_SAVE = true` in config
2. Character ID is being set correctly
3. Backend logs show inventory requests

**Test manually:**
```bash
curl -X POST http://your-api:6701/v1/inventory/set \
  -H 'Content-Type: application/json' \
  -d '{
    "character_id": "test-char-id",
    "server_id": "your-server-id",
    "slots": {"0": {"item": "Bandage", "quantity": 1}}
  }'
```

---

## 🔐 Security Notes

### For Production:

1. **Use HTTPS** - Deploy backend with SSL certificate
2. **Firewall** - Restrict API access to only your DayZ server IPs
3. **Authentication** - Backend validates server tokens (already implemented)
4. **Rate Limiting** - Consider adding rate limits in production

---

## 🚀 Advanced Usage

### Multi-Server Cross-Transfer

Configure multiple servers with the **same cluster ID**:

```cpp
// Server 1 (New York)
static string CLUSTER_ID = "us-east-cluster";
static string SERVER_ID = "ny-server-1";

// Server 2 (LA)
static string CLUSTER_ID = "us-east-cluster";  // Same cluster
static string SERVER_ID = "la-server-2";       // Different server
```

Once the remaining lifecycle hooks are wired, this flow can support server transfers. In the current code, treat this as a design target rather than a verified feature.

### Custom Inventory Sync

Extend `HiveApiClient.c` for custom data:

```cpp
static void SaveCustomData(string characterID, string customJson)
{
    string url = HiveApiConfig.API_URL + "/v1/characters/custom";
    // ... implement custom sync
}
```

---

## 📝 File Structure

```
HiveApiMod/
|-- README.md (this file)
|-- config.cpp                      # Mod metadata
|-- mod.cpp                         # Mod definition
`-- scripts/
    `-- 4_world/
        |-- HiveApiConfig.c         # Configuration
        |-- HiveApiClient.c         # API wrapper class
        |-- HiveApiCharacterSync.c  # Sync manager
        `-- classes/
            `-- useractionscomponent/
                `-- HiveActionPlayerSync.c  # Player event hooks
```

---

## 📚 Additional Resources

- **Backend Deployment:** See `/DEPLOYMENT_GUIDE.md`
- **API Reference:** `http://your-api:6701/docs` for the host-mapped local stack, or `:8000` inside the compose network
- **Integration Examples:** See `/INTEGRATION_EXAMPLES.md`
- **Community Tools:** See `/RESOURCES.md`

---

## [done] Checklist

Before going live:

- [ ] Backend deployed and accessible
- [ ] Backend health check returns success
- [ ] Demo data created (or production data)
- [ ] Mod configured with correct API URL
- [ ] Cluster ID and Server ID set
- [ ] Mod built and packed
- [ ] Server started with mod loaded
- [ ] Test player join/leave works
- [ ] Inventory sync confirmed
- [ ] Logs show successful API calls

---

**Happy modding! 🎮**

For issues or questions, check the main repository documentation.
