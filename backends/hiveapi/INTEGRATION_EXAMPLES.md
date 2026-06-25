# 🔌 Integration Examples - Using HiveAPI with DayZ

These examples show how to integrate HiveAPI with your DayZ server mod.

## 📋 Table of Contents

1. [C++ Enforce Script Examples](#c-enforce-script-examples)
2. [Python Bot Examples](#python-bot-examples)
3. [Discord Bot Examples](#discord-bot-examples)
4. [Web App Examples](#web-app-examples)

---

## C++ Enforce Script Examples

### 1. Server Login (Authenticate Server)

```cpp
// ServerLogin.c
class ServerLogin
{
    void LoginToHiveAPI()
    {
        string serverID = "your-server-uuid";
        string apiURL = "https://your-hiveapi.com/v1/auth/server-login";

        // Create request
        RestContext ctx = new RestContext();
        ctx.SetHeader("Content-Type: application/json");

        // Build payload
        JsonDataBody body = new JsonDataBody();
        body.Set("server_id", serverID);

        // Send request
        RestApi.Post(ctx, apiURL, body, this, "OnLoginResponse");
    }

    void OnLoginResponse(RestApi api, int code, string data)
    {
        if (code == 200)
        {
            // Parse JWT token
            JsonDataParser parser = new JsonDataParser();
            JsonDataReader reader = parser.Parse(data);

            string accessToken = reader.Get("access_token");
            Print("[done] Logged in! Token: " + accessToken);

            // Store token for future requests
            g_Game.SetHiveToken(accessToken);
        }
        else
        {
            Print("FAIL Login failed: " + code);
        }
    }
}
```

### 2. Claim Character on Server Join

```cpp
// CharacterClaim.c
class CharacterManager
{
    void ClaimCharacterForPlayer(PlayerIdentity identity, string clusterID)
    {
        string apiURL = "https://your-hiveapi.com/v1/characters/claim";
        string steamID = identity.GetPlainId();
        string serverID = g_Game.GetServerID();

        // Build request
        RestContext ctx = new RestContext();
        ctx.SetHeader("Content-Type: application/json");
        ctx.SetHeader("Authorization: Bearer " + g_Game.GetHiveToken());

        // Build payload
        JsonDataBody body = new JsonDataBody();
        body.Set("platform_uid", "steam:" + steamID);
        body.Set("cluster_id", clusterID);
        body.Set("server_id", serverID);

        // Add spawn position
        JsonDataBody position = new JsonDataBody();
        position.Set("x", 7500.0);
        position.Set("y", 300.0);
        position.Set("z", 7500.0);
        body.Set("position", position);

        // Send request
        RestApi.Post(ctx, apiURL, body, this, "OnClaimResponse");
    }

    void OnClaimResponse(RestApi api, int code, string data)
    {
        if (code == 200)
        {
            JsonDataParser parser = new JsonDataParser();
            JsonDataReader reader = parser.Parse(data);

            string characterID = reader.Get("id");
            string lifeState = reader.Get("life_state");

            Print("[done] Character claimed: " + characterID);
            Print("   Life state: " + lifeState);

            // Load character data...
        }
        else
        {
            Print("FAIL Character claim failed: " + code);
        }
    }
}
```

### 3. Sync Inventory to HiveAPI

```cpp
// InventorySync.c
class InventoryManager
{
    void SyncInventoryToHive(string characterID, PlayerBase player)
    {
        string apiURL = "https://your-hiveapi.com/v1/inventory/set";
        string serverID = g_Game.GetServerID();

        // Build inventory data
        JsonDataBody slots = new JsonDataBody();

        int slotIndex = 0;
        for (int i = 0; i < player.GetInventory().GetAttachmentSlotsCount(); i++)
        {
            EntityAI item = player.GetInventory().GetAttachmentFromIndex(i);
            if (item)
            {
                JsonDataBody slot = new JsonDataBody();
                slot.Set("item", item.GetType());
                slot.Set("quantity", item.GetQuantity());
                slot.Set("health", item.GetHealth());

                slots.Set(slotIndex.ToString(), slot);
                slotIndex++;
            }
        }

        // Build request
        RestContext ctx = new RestContext();
        ctx.SetHeader("Content-Type: application/json");
        ctx.SetHeader("Authorization: Bearer " + g_Game.GetHiveToken());

        JsonDataBody body = new JsonDataBody();
        body.Set("character_id", characterID);
        body.Set("server_id", serverID);
        body.Set("slots", slots);

        // Send request
        RestApi.Post(ctx, apiURL, body, this, "OnInventorySyncResponse");
    }

    void OnInventorySyncResponse(RestApi api, int code, string data)
    {
        if (code == 200)
        {
            JsonDataParser parser = new JsonDataParser();
            JsonDataReader reader = parser.Parse(data);

            string checksum = reader.Get("checksum");
            bool conflict = reader.Get("conflict");

            if (!conflict)
            {
                Print("[done] Inventory synced! Checksum: " + checksum);
            }
            else
            {
                Print("⚠️ Inventory conflict detected!");
                // Handle conflict...
            }
        }
    }
}
```

### 4. Character Heartbeat (Keep-Alive)

```cpp
// CharacterHeartbeat.c
class HeartbeatManager
{
    void SendHeartbeat(string characterID, PlayerBase player)
    {
        string apiURL = "https://your-hiveapi.com/v1/characters/heartbeat";
        string serverID = g_Game.GetServerID();

        // Get player position
        vector pos = player.GetPosition();

        // Build request
        RestContext ctx = new RestContext();
        ctx.SetHeader("Content-Type: application/json");
        ctx.SetHeader("Authorization: Bearer " + g_Game.GetHiveToken());

        // Build payload
        JsonDataBody body = new JsonDataBody();
        body.Set("character_id", characterID);
        body.Set("server_id", serverID);

        // Position
        JsonDataBody position = new JsonDataBody();
        position.Set("x", pos[0]);
        position.Set("y", pos[1]);
        position.Set("z", pos[2]);
        body.Set("position", position);

        // Stats
        JsonDataBody stats = new JsonDataBody();
        stats.Set("health", player.GetHealth());
        stats.Set("blood", player.GetBlood());
        body.Set("stats", stats);

        // Send request
        RestApi.Post(ctx, apiURL, body, this, "OnHeartbeatResponse");
    }

    void OnHeartbeatResponse(RestApi api, int code, string data)
    {
        if (code == 200)
        {
            Print("[done] Heartbeat sent successfully");
        }
    }
}
```

---

## Python Bot Examples

### Simple Character Lookup

```python
import requests

class HiveAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None

    def get_events(self, limit: int = 100, event_type: str = None):
        """Get recent events from HiveAPI."""
        params = {"limit": limit}
        if event_type:
            params["event_type"] = event_type

        response = requests.get(
            f"{self.base_url}/v1/admin/events",
            params=params
        )
        response.raise_for_status()
        return response.json()

    def get_overview(self):
        """Get system overview stats."""
        response = requests.get(f"{self.base_url}/v1/admin/overview")
        response.raise_for_status()
        return response.json()


# Usage
client = HiveAPIClient("http://localhost:8000")

# Get stats
stats = client.get_overview()
print(f"Players: {stats['players']}")
print(f"Characters: {stats['characters']}")
print(f"Servers: {stats['servers']}")

# Get recent character events
events = client.get_events(limit=10, event_type="character_created")
for event in events:
    print(f"Character created: {event['object_id']} at {event['timestamp']}")
```

---

## Discord Bot Examples

### Discord Bot for Player Stats

```python
import discord
from discord.ext import commands
import requests

bot = commands.Bot(command_prefix='!')
HIVEAPI_URL = "http://localhost:8000"

@bot.command(name='stats')
async def server_stats(ctx):
    """Show server cluster stats."""
    try:
        response = requests.get(f"{HIVEAPI_URL}/v1/admin/overview")
        response.raise_for_status()
        data = response.json()

        embed = discord.Embed(
            title="🎮 DayZ Cluster Stats",
            color=discord.Color.blue()
        )
        embed.add_field(name="👥 Players", value=data['players'], inline=True)
        embed.add_field(name="🏃 Characters", value=data['characters'], inline=True)
        embed.add_field(name="🖥️ Servers", value=data['servers'], inline=True)
        embed.add_field(name="📊 Events (24h)", value=data['recent_events'], inline=True)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"FAIL Error fetching stats: {str(e)}")

@bot.command(name='events')
async def recent_events(ctx, limit: int = 5):
    """Show recent events."""
    try:
        response = requests.get(
            f"{HIVEAPI_URL}/v1/admin/events",
            params={"limit": limit}
        )
        response.raise_for_status()
        events = response.json()

        embed = discord.Embed(
            title=f"📋 Recent Events (Last {limit})",
            color=discord.Color.green()
        )

        for event in events[:5]:
            event_type = event['type']
            timestamp = event['timestamp']
            server_id = event.get('server_id', 'Unknown')[:8]

            embed.add_field(
                name=f"{event_type}",
                value=f"Server: {server_id}\nTime: {timestamp}",
                inline=False
            )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"FAIL Error fetching events: {str(e)}")

bot.run('YOUR_DISCORD_BOT_TOKEN')
```

---

## Web App Examples

### React Component for Live Events

```typescript
// LiveEvents.tsx
import { useState, useEffect } from 'react';

interface Event {
  id: string;
  type: string;
  timestamp: string;
  server_id: string;
  object_id: string;
}

export function LiveEvents() {
  const [events, setEvents] = useState<Event[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    // Connect to SSE stream
    const eventSource = new EventSource('http://localhost:8000/v1/admin/events/stream');

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents((prev) => [data, ...prev].slice(0, 50));
      setConnected(true);
    };

    eventSource.onerror = () => {
      setConnected(false);
    };

    return () => {
      eventSource.close();
    };
  }, []);

  return (
    <div>
      <h2>
        Live Events
        <span className={connected  'connected' : 'disconnected'}>
          {connected  '🟢' : '🔴'}
        </span>
      </h2>

      <div>
        {events.map((event) => (
          <div key={event.id} className="event">
            <span className="type">{event.type}</span>
            <span className="time">{new Date(event.timestamp).toLocaleTimeString()}</span>
            {event.object_id && <span>Object: {event.object_id.substring(0, 8)}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 🎯 Common Patterns

### Authentication Flow

```
1. Server starts -> Call /v1/auth/server-login with server_id
2. Receive JWT token
3. Store token in memory
4. Use token in Authorization header for all requests
5. Token expires after 60 minutes -> Re-authenticate
```

### Character Transfer Flow

```
1. Player logs out on Server A -> Call /v1/characters/heartbeat with final state
2. Server A -> Call /v1/inventory/set with final inventory
3. Player connects to Server B -> Call /v1/characters/claim
4. Server B receives character data
5. Server B loads character with inventory
6. Server B -> Call /v1/characters/heartbeat to confirm ownership
```

### Inventory Sync Pattern

```
1. Every 60 seconds -> Call /v1/inventory/set with current inventory
2. Include client_checksum
3. If conflict detected -> Fetch latest from API
4. If no conflict -> Continue
```

---

## 📚 Additional Resources

- **API Docs**: http://localhost:8000/docs
- **Project Overview**: [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)
- **Quick Start**: [QUICK_START.md](QUICK_START.md)

---

**Need help with integration** The API is well-documented and ready to use!
