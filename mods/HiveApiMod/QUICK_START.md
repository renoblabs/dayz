# 🚀 Quick Start - HiveAPI Mod

**Prototype setup guide for connecting a DayZ server to HiveAPI.**

> Current status: this guide describes the intended wiring, but the active Enforce mod is still a scaffold. Server login, claim, heartbeat, and inventory request helpers exist; Bearer token use, character-id handoff, restore, periodic autosave, reliable disconnect save, and transfer behavior are not fully wired or verified yet.

---

## Step 1: Deploy the Backend (5 min)

### If you haven't deployed the backend yet:

```bash
# On your server/VPS (Ubuntu):
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

git clone https://github.com/renoblabs/dayz.git
cd dayz/backends/hiveapi/ops
docker compose up -d --build

# Wait 30 seconds, then test:
curl http://localhost:6701/health
```

**Result:** Backend running at `http://YOUR-SERVER-IP:6701` on the host-mapped local stack, or `:8000` inside the compose network.

**Need detailed deployment help** See `/DEPLOYMENT_GUIDE.md`

---

## Step 2: Get Your IDs (2 min)

### Create demo data to get cluster and server IDs:

```bash
cd dayz/backends/hiveapi
# Use the repo seed/bootstrap flow, or POST /v1/server-stub/bootstrap in dev
```

**Copy these from the output:**
- `Cluster ID: abc-123-def-456...`
- `Server ID: xyz-789-ghi-012...`

**Alternative:** Create your own UUIDs at https://www.uuidgenerator.net/

---

## Step 3: Configure the Mod (1 min)

### Edit `scripts/3_game/HiveApiConfig.c` or `$profile:hiveapi_config.json`:

```cpp
// Change these three lines:
static string API_URL = "http://YOUR-VPS-IP:6701";         // Your backend URL
static string CLUSTER_ID = "abc-123-def-456...";           // From step 2
static string SERVER_ID = "xyz-789-ghi-012...";            // From step 2
```

**Example:**
```cpp
static string API_URL = "http://192.168.1.100:6701";
static string CLUSTER_ID = "550e8400-e29b-41d4-a716-446655440000";
static string SERVER_ID = "660e8400-e29b-41d4-a716-446655440001";
```

---

## Step 4: Copy Files to Your Mod (2 min)

### Copy this entire folder structure to your mod:

```
YourDayZMod/
`-- HiveApiMod/              ← Copy this entire folder
    |-- config.cpp
    `-- scripts/
        `-- 4_world/
            |-- HiveApiConfig.c
            |-- HiveApiClient.c
            `-- HiveApiCharacterSync.c
```

**Or create a new standalone prototype mod:**
- Use the `HiveApiMod/` folder as a starting point
- Finish the lifecycle hooks before treating it as production-ready

---

## Step 5: Build and Pack (3 min)

### Using DayZ Tools:

1. Open **DayZ Tools Workbench**
2. File -> Open -> Select your mod folder
3. Build -> Pack
4. Output: `@HiveApiMod` folder in your DayZ directory

**Using command line (advanced):**
```bash
# Assuming Workbench tools are in PATH
DayZTools.exe -pack YourModFolder @HiveApiMod
```

---

## Step 6: Add to Server (1 min)

### Edit your server start parameters:

**Before:**
```
DayZServer_x64.exe -config=serverDZ.cfg -port=2302
```

**After:**
```
DayZServer_x64.exe -config=serverDZ.cfg -port=2302 -mod=@HiveApiMod
```

**With other mods:**
```
-mod=@CF;@YourOtherMod;@HiveApiMod
```

### Restart your DayZ server.

---

## Step 7: Test It (2 min)

### Watch the server logs on startup:

**Look for:**
```
[HiveAPI] Mission server initialized
[HiveAPI] Configuration loaded:
[HiveAPI]   API URL: http://192.168.1.100:6701
[HiveAPI]   Cluster: 550e8400-e29b-41d4-a716-446655440000
[HiveAPI]   Server: 660e8400-e29b-41d4-a716-446655440001
[HiveAPI] Authenticating server: 660e8400-e29b-41d4-a716-446655440001
[HiveAPI] [OK] Server authenticated successfully
```

### Join your server as a player:

**Look for:**
```
[HiveAPI] Player connecting: Steam:76561198XXXXXXXX
[HiveAPI] Claiming character for Steam:76561198XXXXXXXX
[HiveAPI] [OK] Character claimed: abc-123-character-id
```

The current callback logs the returned character ID but does not yet store it in `HiveApiCharacterSync.c`, so later save/heartbeat calls still need that handoff before they are reliable.

### Disconnect from server:

**Current reality:**
```
[HiveAPI] Player disconnecting: Steam:76561198XXXXXXXX
[HiveAPI DEBUG] No character ID for Steam:76561198XXXXXXXX
```

Inventory save is the intended path, but it is not expected to work until character-id handoff is wired.

---

## Current checkpoint

At this point you have validated backend reachability and the first login/claim calls. Do not treat this as production persistence yet.

### What's working:
- Server authentication route and mod call
- Character claim route and mod call
- Inventory and heartbeat request helpers

### Still WIP:
- Bearer token attachment on follow-up requests
- Character ID storage after claim
- Restore-on-join
- Periodic autosave
- Reliable disconnect save
- Cross-server transfer behavior

---

## 🎯 Next Steps

### View activity in the dashboard:

```bash
# On your local machine:
cd dayz/frontends/web-ui
npm install
npm run dev

# Open http://localhost:3000
# This is primarily the BossSignal operator dashboard, not a completed Hive persistence UI.
```

### Test cross-server transfer:

1. Set up second DayZ server with **same CLUSTER_ID**, different SERVER_ID
2. Join Server 1, get some items
3. Disconnect and join Server 2
4. Expected design target: character and items transfer automatically after the remaining lifecycle hooks are implemented and verified.

---

## 🐛 Troubleshooting

### Server logs show "API_URL not configured!"

**Fix:** Edit `HiveApiConfig.c` and set `API_URL`, `CLUSTER_ID`, `SERVER_ID`

### Server logs show "Server login failed"

**Fix:**
1. Check backend is running: `curl http://YOUR-API:6701/health` for the host-mapped stack, or `:8000` inside compose
2. Check firewall allows the host-mapped API port
3. Enable debug logging: Set `DEBUG_LOGGING = true` in `HiveApiConfig.c`

### No character claimed when player joins

**Fix:**
1. Check server authenticated successfully in logs
2. Check `CLUSTER_ID` and `SERVER_ID` are valid UUIDs
3. Test backend: `curl http://YOUR-API:6701/v1/admin/overview`

### Inventory not saving

**Fix:**
1. Verify `ENABLE_AUTO_SAVE = true` in config
2. Check character_id is being set (look for "Character claimed" in logs)
3. Test inventory API manually:
```bash
curl -X POST http://YOUR-API:6701/v1/inventory/set \
  -H 'Content-Type: application/json' \
  -d '{"character_id":"test","server_id":"test","slots":{}}'
```

---

## 📊 Monitoring

### Check backend health:
```bash
curl http://YOUR-API:6701/health
```

### View system stats:
```bash
curl http://YOUR-API:6701/v1/admin/overview
```

### View recent events:
```bash
curl http://YOUR-API:6701/v1/admin/eventslimit=10
```

### View backend logs:
```bash
cd dayz/backends/hiveapi/ops
docker compose logs -f api
```

---

## 🔧 Advanced Configuration

### Enable debug logging:

```cpp
// In HiveApiConfig.c:
static bool DEBUG_LOGGING = true;
```

### Adjust auto-save interval:

```cpp
// Save every 10 minutes instead of 5:
static int SAVE_INTERVAL_SECONDS = 600;

// Disable auto-save (manual only):
static int SAVE_INTERVAL_SECONDS = 0;
```

### Change request timeout:

```cpp
// For slow networks, increase timeout:
static int REQUEST_TIMEOUT_MS = 10000;  // 10 seconds
```

---

## 🎮 Multiple Servers Setup

### Design target for cross-server transfers:

This is not production-ready yet. Use matching clusters only after restore/save and character ownership have been validated.

**Server 1 (New York):**
```cpp
static string API_URL = "http://api.myserver.com:6701";
static string CLUSTER_ID = "us-cluster-001";      // Same cluster
static string SERVER_ID = "ny-server-001";        // Different ID
```

**Server 2 (LA):**
```cpp
static string API_URL = "http://api.myserver.com:6701";  // Same API
static string CLUSTER_ID = "us-cluster-001";             // Same cluster!
static string SERVER_ID = "la-server-001";               // Different ID
```

**Design result:** Players transfer between NY and LA servers after the remaining lifecycle hooks are implemented and verified.

---

## 📝 Files You Need

**Minimum required files:**
- `config.cpp` - Mod configuration
- `scripts/3_game/HiveApiConfig.c` - Your settings (EDIT THIS)
- `scripts/4_world/HiveApiClient.c` - API wrapper
- `scripts/5_mission/HiveApiCharacterSync.c` - Sync logic

**Total size:** ~20KB

---

## ❓ Still Having Issues

1. **Enable debug logging** in `HiveApiConfig.c`
2. **Check server logs** for HiveAPI messages
3. **Test backend** with curl commands
4. **Check firewall** allows the host-mapped API port
5. **Verify IDs** are valid UUIDs

**Full documentation:** See `README.md` in this folder

---

**Happy gaming! 🎮**

Your DayZ server is now running with HiveAPI!
