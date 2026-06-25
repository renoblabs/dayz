# Testing & Demo Guide

This guide walks through testing the HiveAPI system and demonstrates its features.

---

## Quick Test Run

### Start the Stack

```bash
# Start backend services
cd hiveapi/ops
docker compose up -d --build

# Wait ~30 seconds for initialization
```

### Create Test Data

```bash
# Generate sample data
cd hiveapi
python scripts/demo_seed.py
```

This creates:
- 1 tenant and cluster
- 4 servers (Toronto, Montreal, Vancouver, Chicago)
- 9 players with characters
- 50+ events over 7 days

### Start the Dashboard

```bash
cd web-ui
npm install
npm run dev
```

Access at http://localhost:3000

---

## Feature Walkthrough

### 1. API Documentation

**URL:** http://localhost:8000/docs

Interactive Swagger UI showing all endpoints. You can test requests directly from the browser.

### 2. Health Check

```bash
curl http://localhost:8000/health
```

Returns system health status.

### 3. System Overview

```bash
curl http://localhost:8000/v1/admin/overview | jq
```

Shows counts of players, characters, servers, and recent events.

### 4. Event History

```bash
curl http://localhost:8000/v1/admin/eventslimit=10 | jq
```

Returns recent events with optional filtering by type, server, or object.

### 5. Real-time Event Stream

The dashboard connects to `/v1/admin/events/stream` via Server-Sent Events to display live updates.

---

## Testing the Workflow

### Server Authentication

```bash
# Get a server ID from the demo seed output
curl -X POST http://localhost:8000/v1/auth/server-login \
  -H 'Content-Type: application/json' \
  -d '{"server_id":"<SERVER_ID>"}' | jq
```

Returns a JWT token for subsequent requests.

### Character Claim

```bash
curl -X POST http://localhost:8000/v1/characters/claim \
  -H 'Content-Type: application/json' \
  -d '{
    "platform_uid": "steam:76561198000000001",
    "cluster_id": "<CLUSTER_ID>",
    "server_id": "<SERVER_ID>",
    "position": {"x": 7500, "y": 300, "z": 7500},
    "stats": {"health": 100, "blood": 5000}
  }' | jq
```

Creates or claims an existing character.

### Inventory Management

```bash
curl -X POST http://localhost:8000/v1/inventory/set \
  -H 'Content-Type: application/json' \
  -d '{
    "character_id": "<CHARACTER_ID>",
    "server_id": "<SERVER_ID>",
    "slots": {
      "0": {"item": "HockeyStick", "quantity": 1},
      "1": {"item": "BeerCan", "quantity": 5}
    }
  }' | jq
```

Sets character inventory. Returns a checksum for conflict detection.

### Inventory Operations

```bash
curl -X POST http://localhost:8000/v1/inventory/apply \
  -H 'Content-Type: application/json' \
  -d '{
    "character_id": "<CHARACTER_ID>",
    "server_id": "<SERVER_ID>",
    "base_checksum": "<CHECKSUM_FROM_PREVIOUS_SET>",
    "ops": [
      {"op": "set", "path": ["slots", "2"], "value": {"item": "Bandage", "quantity": 3}}
    ]
  }' | jq
```

Applies operations with conflict detection. Returns error if base checksum doesn't match.

---

## Running Tests

```bash
cd hiveapi
pytest -v
```

Test suite covers:
- Authentication (server login, invalid credentials)
- Character operations (claim, heartbeat)
- Inventory operations (set, apply, conflicts)
- Admin endpoints (overview, events)

All tests use in-memory SQLite for speed.

---

## Dashboard Features

### Overview Page
- Live player/character/server counts
- Recent events (24h)
- Real-time event stream via SSE

### Events Page
- Full event history
- Filter by limit (50/100/500/1000)
- Export to JSON

---

## Performance Testing

### Load Testing with curl

```bash
# Simple load test
for i in {1..100}; do
  curl -s http://localhost:8000/health > /dev/null &
done
wait
```

### Monitor with Prometheus

**URL:** http://localhost:9090

Query examples:
- `hiveapi_requests_total` - Total requests
- `hiveapi_request_duration_seconds` - Latency

### Visualize with Grafana

**URL:** http://localhost:3000
**Credentials:** admin / admin

Pre-configured to pull metrics from Prometheus.

---

## Common Test Scenarios

### Cross-Server Transfer

1. Player on Server A calls `/characters/heartbeat` with position/inventory
2. Player disconnects from Server A
3. Player connects to Server B
4. Server B calls `/characters/claim` for same platform_uid
5. Character data loads with position/inventory intact

### Conflict Detection

1. Server A sets inventory (receives checksum)
2. Server B sets inventory for same character
3. Server A tries to apply ops with old checksum
4. API returns conflict error with current checksum
5. Server A fetches latest, resolves, retries

### Event Auditing

1. Perform any operation (claim, inventory set, etc.)
2. Check `/admin/events` - operation is logged
3. Dashboard updates in real-time via SSE
4. Export events for analysis

---

## Troubleshooting Tests

### API Not Responding

```bash
# Check if containers are running
docker compose ps

# View logs
docker compose logs api

# Restart if needed
docker compose restart api
```

### Database Issues

```bash
# Check database
docker compose logs db

# Connect to database
docker compose exec db psql -U postgres -d hive
```

### Frontend Issues

```bash
# Check browser console for errors
# Verify API is accessible
curl http://localhost:8000/health

# Check vite proxy settings
cat web-ui/vite.config.ts
```

### Tests Failing

```bash
# Run with verbose output
pytest -vv

# Run specific test file
pytest tests/test_auth.py -v

# Check for import errors
python -c "from app.main import app; print('OK')"
```

---

## Integration Testing

### C++ Integration

See [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md) for DayZ Enforce scripts.

### Python Integration

```python
import requests

# Test connection
response = requests.get("http://localhost:8000/health")
assert response.status_code == 200

# Get overview
response = requests.get("http://localhost:8000/v1/admin/overview")
data = response.json()
print(f"Players: {data['players']}")
```

### Discord Bot Integration

See [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md) for Discord bot examples.

---

## Cleanup

```bash
# Stop services
make stop

# Or with docker compose
cd hiveapi/ops
docker compose down

# Remove all data
make clean
# Or
docker compose down -v
```

---

## Next Steps

- Review [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md) for implementation patterns
- Check [RESOURCES.md](RESOURCES.md) for related DayZ tools
- See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for architecture details

---

This system is ready to integrate with DayZ servers. All endpoints are documented at http://localhost:8000/docs.
