# ⚡ Quick Start Guide

Get the DayZ HiveAPI running in **less than 5 minutes**!

---

## 📋 Prerequisites

### Required
- **Docker** and **Docker Compose** (for backend)
- **Node.js 18+** (for web UI)

### Optional
- **Make** (for convenience commands)
- **PostgreSQL** (if not using Docker)
- **Redis** (if not using Docker)

---

## 🚀 Method 1: Lightning Fast (Recommended)

### One Command to Rule Them All

```bash
make all
```

**That's it!** This command:
1. Starts the entire backend stack (API, database, cache, monitoring)
2. Creates realistic demo data (4 servers, 9 players, 50+ events)
3. Shows you the next steps

**Access your system:**
- 🌐 Dashboard: Open browser, run `cd web-ui && npm install && npm run dev`, then visit http://localhost:3000
- 📚 API Docs: http://localhost:8000/docs
- ❤️ Health Check: http://localhost:8000/health

---

## 🛠️ Method 2: Step-by-Step

Perfect if you want to see each component start up.

### Step 1: Start the Backend

```bash
make start

# Or without Make:
cd hiveapi/ops
docker compose up -d --build
```

**Wait 30 seconds** for everything to initialize.

**Verify it's running:**
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": 1234567890.123
}
```

### Step 2: Create Demo Data

```bash
make demo

# Or without Make:
cd hiveapi
python scripts/demo_seed.py
```

**This creates:**
- 1 Tenant ("Hockey Apocalypse Network")
- 1 Cluster ("North American Cluster")
- 4 Servers (Toronto, Montreal, Vancouver, Chicago)
- 9 Players with sample Steam IDs
- 9-18 Characters with inventory and stats
- 50+ Events over the past 7 days

**Why sample data** Gives the endpoints data to return and helps you understand the data model. All of it is synthetic.

### Step 3: Start the Web UI

```bash
make ui

# Or without Make:
cd web-ui
npm install
npm run dev
```

**Access the dashboard:** http://localhost:3000

### Step 4: Run Tests (Optional)

```bash
make test

# Or without Make:
cd hiveapi
pytest -v
```

**You should see all green checkmarks!** [done]

---

## 🎯 Method 3: Manual Setup (No Docker)

If you can't or don't want to use Docker:

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Node.js 18+

### Step 1: Setup PostgreSQL

```bash
# Create database
createdb hive

# Set environment variable
export DB_URL="postgresql+psycopg://postgres:postgres@localhost:5432/hive"
```

### Step 2: Setup Redis

```bash
# Start Redis (if not running)
redis-server

# Set environment variable
export REDIS_URL="redis://localhost:6379/0"
```

### Step 3: Install Python Dependencies

```bash
cd hiveapi
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4: Run Database Migrations

```bash
cd hiveapi
alembic upgrade head
```

### Step 5: Create Demo Data

```bash
python scripts/demo_seed.py
```

### Step 6: Start the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**API is now running at:** http://localhost:8000

### Step 7: Start the Web UI

```bash
cd web-ui
npm install
npm run dev
```

**Dashboard is now at:** http://localhost:3000

---

## [done] Verify Everything Works

### 1. Check API Health

```bash
curl http://localhost:8000/health
```

**Expected:** `{"status": "healthy", "timestamp": ...}`

### 2. Get System Overview

```bash
curl http://localhost:8000/v1/admin/overview
```

**Expected:** Stats showing players, characters, servers, events

### 3. View Interactive Docs

Open: http://localhost:8000/docs

**You should see Swagger UI with all endpoints listed**

### 4. Check Web Dashboard

Open: http://localhost:3000

**You should see:**
- Live stats (players, characters, servers, events)
- Real-time event stream
- Navigation to Events page

---

## 🎮 Next Steps: Test the API

### 1. View Demo Data

```bash
# See all events
curl http://localhost:8000/v1/admin/eventslimit=10 | jq

# Get overview stats
curl http://localhost:8000/v1/admin/overview | jq
```

### 2. Test Server Login

Get a server ID from the demo seed output, then:

```bash
curl -X POST http://localhost:8000/v1/auth/server-login \
  -H 'Content-Type: application/json' \
  -d '{"server_id":"<SERVER_ID_FROM_DEMO_SEED>"}'
```

**You should get back a JWT token!**

### 3. Claim a Character

```bash
curl -X POST http://localhost:8000/v1/characters/claim \
  -H 'Content-Type: application/json' \
  -d '{
    "platform_uid": "steam:76561198000000001",
    "cluster_id": "<CLUSTER_ID>",
    "server_id": "<SERVER_ID>",
    "position": {"x": 7500, "y": 300, "z": 7500},
    "stats": {"health": 100, "blood": 5000}
  }'
```

### 4. Set Inventory

```bash
curl -X POST http://localhost:8000/v1/inventory/set \
  -H 'Content-Type: application/json' \
  -d '{
    "character_id": "<CHARACTER_ID_FROM_ABOVE>",
    "server_id": "<SERVER_ID>",
    "slots": {
      "0": {"item": "HockeyStick", "quantity": 1},
      "1": {"item": "BeerCan", "quantity": 5},
      "2": {"item": "GoalieMask_Gold", "quantity": 1}
    }
  }'
```

### 5. Watch Events Update

Go to the dashboard (http://localhost:3000) and watch the **Events** section update in real-time!

---

## 🔧 Useful Commands

### Using Make (Recommended)

```bash
make start    # Start backend stack
make stop     # Stop backend stack
make restart  # Restart backend stack
make demo     # Create demo data
make ui       # Start web UI
make test     # Run test suite
make logs     # View backend logs
make status   # Check service status
make clean    # Clean up Docker volumes
make fresh    # Fresh start (clean + start + demo)
make help     # See all commands
```

### Using Docker Compose

```bash
# Start
cd hiveapi/ops
docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f

# Check status
docker compose ps

# Restart specific service
docker compose restart api

# Shell into API container
docker compose exec api /bin/bash

# Database shell
docker compose exec db psql -U postgres -d hive

# Redis CLI
docker compose exec redis redis-cli
```

---

## 🐛 Troubleshooting

### Docker Issues

**Problem:** `docker: command not found`
**Solution:** Install Docker Desktop or Docker Engine

**Problem:** Port 8000 already in use
**Solution:**
```bash
# Find what's using port 8000
lsof -i :8000

# Kill it or change port in docker-compose.yml
```

**Problem:** Containers won't start
**Solution:**
```bash
# Check logs
docker compose logs

# Clean everything and restart
make fresh
```

### API Issues

**Problem:** Can't connect to http://localhost:8000
**Solution:**
```bash
# Check if API container is running
docker compose ps

# Check logs
docker compose logs api

# Try health check
curl http://localhost:8000/health
```

**Problem:** Database connection errors
**Solution:**
```bash
# Ensure PostgreSQL container is running
docker compose ps db

# Check database logs
docker compose logs db
```

### Web UI Issues

**Problem:** `npm install` fails
**Solution:**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and try again
rm -rf node_modules
npm install
```

**Problem:** Can't connect to API from UI
**Solution:**
- Ensure API is running on port 8000
- Check browser console for CORS errors
- Verify vite.config.ts proxy settings

**Problem:** Dashboard shows no data
**Solution:**
```bash
# Make sure you ran the demo seed
make demo

# Or manually:
cd hiveapi
python scripts/demo_seed.py
```

### Test Issues

**Problem:** Tests fail
**Solution:**
```bash
# Ensure you're in the right directory
cd hiveapi

# Install test dependencies
pip install -r requirements.txt

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_auth.py -v
```

---

## 📊 What's Running

After `make all`, you'll have these services:

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| **API** | 8000 | http://localhost:8000 | FastAPI backend |
| **Dashboard** | 3000 | http://localhost:3000 | React UI (when started) |
| **PostgreSQL** | 5432 | localhost:5432 | Database |
| **Redis** | 6379 | localhost:6379 | Cache |
| **Prometheus** | 9090 | http://localhost:9090 | Metrics |
| **Grafana** | 3000 | http://localhost:3000 | Visualization |

---

## 🎯 Common Tasks

### View System Stats

```bash
# Using API
curl http://localhost:8000/v1/admin/overview | jq

# Using Dashboard
# Open http://localhost:3000
```

### Export Events

**Via Dashboard:**
1. Go to http://localhost:3000/events
2. Click "Export" button
3. Save JSON file

**Via API:**
```bash
curl http://localhost:8000/v1/admin/eventslimit=1000 > events.json
```

### Check Logs

```bash
# All services
make logs

# Specific service
docker compose logs api
docker compose logs db
```

### Reset Everything

```bash
# Clean slate
make fresh

# Or manually
make clean
make all
```

---

## 🚀 What's Next

Now that everything is running:

1. **📖 Read the docs:** [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for architecture
2. **🎬 Try the demo:** [DEMO_GUIDE.md](DEMO_GUIDE.md) for testing walkthrough
3. **🔌 Integrate:** [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md) for code samples
4. **🛠️ Explore:** [RESOURCES.md](RESOURCES.md) for community tools

---

## 💡 Pro Tips

### Development Workflow

1. **Code changes:** Edit files in `hiveapi/app/`
2. **Auto-reload:** FastAPI reloads automatically
3. **Test:** Run `make test` frequently
4. **Commit:** Use clear commit messages

### Performance Tips

- Use `make start` instead of `docker compose up` for convenience
- Keep Docker Desktop running for better performance
- Use `make logs` to monitor issues
- Check Prometheus at http://localhost:9090 for metrics

### Learning Tips

- **Start with API docs:** http://localhost:8000/docs
- **Use the dashboard:** Visual understanding of data
- **Read the tests:** `hiveapi/tests/` shows usage examples
- **Check integration examples:** Real code you can copy

---

## 🎁 Bonus: Quick Demo Script

Perfect for showing someone the system:

```bash
# Terminal 1: Start everything
make all

# Terminal 2: Start web UI (after backend is up)
make ui

# Terminal 3: Watch logs
make logs

# Browser: Open http://localhost:3000

# Show them:
# 1. Dashboard with live stats
# 2. Events page with real-time updates
# 3. API docs at /docs
# 4. Export events feature

# Then say: "All this with one command: make all"
```

---

## ❓ Still Stuck

1. **Check logs:** `make logs`
2. **Verify services:** `make status`
3. **Try fresh start:** `make fresh`
4. **Read error messages:** They usually tell you what's wrong
5. **Check environment:** Make sure Docker/Node.js are installed

---

<p align="center">
  <strong>Ready to integrate</strong><br>
  The API is running, the dashboard is live, and you're ready to go.
</p>

<p align="center">
  <strong>Need help integrating with your DayZ server</strong><br>
  Check out <a href="INTEGRATION_EXAMPLES.md">INTEGRATION_EXAMPLES.md</a>
</p>

<p align="center">
  <strong>Happy coding! 🚀</strong>
</p>
