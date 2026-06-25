#!/usr/bin/env python3
"""
BossSignal test harness — simulates a complete boss encounter sequence.

Sends the full event lifecycle to your local backend:
  1. server.started   — server comes online
  2. server.heartbeat — background ping
  3. boss.spawned     — boss appears
  4. server.heartbeat — heartbeat while boss is alive (with health ticking down)
  5. boss.killed      — boss dies, participants listed

Run this BEFORE you have DayZ installed to verify the backend and dashboard
work correctly end-to-end.

Usage:
  python simulate_boss_encounter.py
  python simulate_boss_encounter.py --url http://your-vps:8080 --secret your-secret
  python simulate_boss_encounter.py --server server_03 --boss "The Abomination"
  python simulate_boss_encounter.py --all-servers   # simulate the configured server list
"""

import argparse
import json
import time
import uuid
import random
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("requests not installed. Run: pip install requests")
    sys.exit(1)


# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_URL    = "http://localhost:8080"
DEFAULT_SECRET = "changeme-generate-with-openssl-rand-hex-32"
DEFAULT_SERVER = "server_01"
DEFAULT_BOSS   = "The Warlord"

BOSS_TYPES = [
    ("ExampleBoss_01",    "The Warlord"),
    ("ExampleBoss_02",     "The Abomination"),
    ("ExampleBoss_03",        "Heavy Tank"),
    ("ExampleBoss_04",     "The Necromancer"),
    ("ExampleBoss_05",     "Hunter Elite"),
]

PLAYER_NAMES = [
    "Vasya_Cherenkov", "DarkHunter99", "SurvivalKing", "RaiderZone",
    "NightWalker", "IronMike42", "Chernarus_Wolf", "Stalker_X",
]

WEAPONS = ["AKM", "M4A1", "Winchester70", "FNX45", "SVD", "Mosin9130"]

# Placeholder server list for --all-servers mode. Override with --servers or
# --servers-file (see servers.example.txt) to match your own network.
DEFAULT_SERVER_IDS = [
    "server_01", "server_02", "server_03",
]


def load_servers_file(path: str) -> list[str]:
    """Read a servers file: one server_id per line, # comments allowed, blanks skipped."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    out = []
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    if not out:
        raise ValueError(f"{path} contained no server ids")
    return out


def resolve_server_ids(args) -> list[str]:
    """Figure out which server IDs to use based on flags.

    Precedence: --servers-file > --servers > DEFAULT_SERVER_IDS.
    Use this for --all-servers mode.
    """
    if args.servers_file:
        return load_servers_file(args.servers_file)
    if args.servers:
        return [s.strip() for s in args.servers.split(",") if s.strip()]
    return DEFAULT_SERVER_IDS


def parse_args():
    p = argparse.ArgumentParser(description="BossSignal test harness")
    p.add_argument("--url",          default=DEFAULT_URL,    help="Backend URL")
    p.add_argument("--secret",       default=DEFAULT_SECRET, help="Shared secret")
    p.add_argument("--server",       default=DEFAULT_SERVER, help="Server ID (single-server mode)")
    p.add_argument("--boss",         default=DEFAULT_BOSS,   help="Boss display name")
    p.add_argument("--delay",        type=float, default=1.5, help="Seconds between events")
    p.add_argument("--all-servers",  action="store_true",    help="Run simulation across the server list (see --servers / --servers-file, else defaults)")
    p.add_argument("--servers",      default=None,           help="Comma-separated server IDs for --all-servers mode (overrides defaults)")
    p.add_argument("--servers-file", default=None,           help="Path to text file (one server_id per line) for --all-servers mode; takes precedence over --servers")
    p.add_argument("--quiet",        action="store_true",    help="Less output")
    return p.parse_args()


class BossSignalClient:
    def __init__(self, base_url: str, secret: str, server_id: str, quiet: bool = False):
        self.base_url  = base_url.rstrip("/")
        self.secret    = secret
        self.server_id = server_id
        self.quiet     = quiet
        self.server_time = 0.0

    def _headers(self):
        return {
            "Content-Type":          "application/json",
            "X-BossSignal-Secret":   self.secret,
            "X-BossSignal-Server":   self.server_id,
            "X-BossSignal-Version":  "0.1.0",
        }

    def post(self, event_type: str, data: dict):
        self.server_time += random.uniform(0.5, 2.0)
        payload = {
            "event_type": event_type,
            "server_id":  self.server_id,
            "server_time": self.server_time,
            "version":    "0.1.0",
            "data":       data,
        }
        try:
            r = requests.post(
                f"{self.base_url}/api/v1/events",
                headers=self._headers(),
                json=payload,
                timeout=5,
            )
            if not self.quiet:
                status_sym = "✓" if r.status_code == 202 else "✗"
                print(f"  {status_sym} [{self.server_id}] {event_type:<28} → HTTP {r.status_code}")
            return r
        except requests.ConnectionError:
            print(f"  ✗ Connection refused — is the backend running at {self.base_url}?")
            sys.exit(1)


def simulate_encounter(client: BossSignalClient, boss_type: str, boss_display: str, delay: float):
    boss_id      = str(uuid.uuid4())[:12]
    max_health   = random.randint(30000, 80000)
    player_count = random.randint(8, 64)
    spawn_pos    = {
        "x": round(random.uniform(1000, 11000), 1),
        "y": 0.0,
        "z": round(random.uniform(1000, 11000), 1),
    }

    print(f"\n  ── Boss: {boss_display} [{boss_type}] ──")
    print(f"     ID={boss_id} hp={max_health} players={player_count}")

    # 1. Boss spawned
    client.post("boss.spawned", {
        "boss_id":            boss_id,
        "boss_type":          boss_type,
        "boss_display_name":  boss_display,
        "spawn_position":     spawn_pos,
        "max_health":         max_health,
        "server_player_count": player_count,
    })
    time.sleep(delay)

    # 2. A few heartbeats while the fight progresses
    num_heartbeats = random.randint(2, 4)
    health_pct = 1.0
    for i in range(num_heartbeats):
        health_pct -= random.uniform(0.15, 0.30)
        health_pct  = max(0.1, health_pct)
        client.post("server.heartbeat", {
            "player_count":      player_count,
            "active_boss_count": 1,
            "active_bosses": [{
                "boss_id":      boss_id,
                "boss_type":    boss_type,
                "display_name": boss_display,
                "elapsed_seconds": delay * (i + 1) * 60,
                "health_pct":   round(health_pct, 2),
            }],
        })
        time.sleep(delay * 0.5)

    # 3. Participants
    num_participants = random.randint(2, min(8, player_count))
    participants = []
    for i in range(num_participants):
        pid  = str(765611980000000 + random.randint(0, 9999999))
        name = random.choice(PLAYER_NAMES)
        dmg  = round(random.uniform(1000, max_health / num_participants * 1.5), 1)
        participants.append({
            "player_id":    pid,
            "player_name":  name,
            "damage_dealt": dmg,
            "kill_shot":    (i == 0),
        })

    killer = participants[0]
    ttk    = random.randint(180, 900)

    # 4. Boss killed
    client.post("boss.killed", {
        "boss_id":            boss_id,
        "boss_type":          boss_type,
        "boss_display_name":  boss_display,
        "time_to_kill_seconds": ttk,
        "max_health":         max_health,
        "spawn_position":     spawn_pos,
        "kill_position": {
            "x": spawn_pos["x"] + random.uniform(-50, 50),
            "y": 0.0,
            "z": spawn_pos["z"] + random.uniform(-50, 50),
        },
        "killer": {
            "player_id":   killer["player_id"],
            "player_name": killer["player_name"],
            "weapon":      random.choice(WEAPONS),
        },
        "participants": participants,
    })

    # Trophy award — pairs with TrophyHunter in real deployment
    trophy_map = {
        "ExampleBoss_01":  "WarlordsCrown",
        "ExampleBoss_02":   "AbominationsJaw",
        "ExampleBoss_03":      "HeavyTankPlate",
        "ExampleBoss_04":   "NecromancersSkull",
        "ExampleBoss_05":   "HuntersFang",
    }
    trophy_class = trophy_map.get(boss_type)
    if trophy_class and participants:
        top = max(participants, key=lambda p: p["damage_dealt"])
        import requests as _rq
        try:
            rows = _rq.get(
                f"{client.base_url}/api/v1/bosses",
                params={"server_id": client.server_id, "limit": 1},
                timeout=3,
            ).json()
            if rows and rows[0].get("id"):
                enc_id = rows[0]["id"]
                client.post("trophy.awarded", {
                    "encounter_id": enc_id,
                    "trophy_class": trophy_class,
                    "boss_type":    boss_type,
                    "holder_id":    top["player_id"],
                    "holder_name":  top["player_name"],
                })
                print(f"  v [{client.server_id}] trophy.awarded {trophy_class} -> {top['player_name']}")
        except Exception as _e:
            print(f"  ! trophy lookup failed: {_e}")

    time.sleep(delay)


def simulate_server(url: str, secret: str, server_id: str, args):
    print(f"\n{'─'*56}")
    print(f"  Server: {server_id}   Backend: {url}")
    print(f"{'─'*56}")

    client = BossSignalClient(url, secret, server_id, quiet=args.quiet)

    # Server startup
    client.post("server.started", {"bosssignal_version": "0.1.0"})
    time.sleep(args.delay * 0.5)

    # Baseline heartbeat
    client.post("server.heartbeat", {
        "player_count":      random.randint(10, 64),
        "active_boss_count": 0,
        "active_bosses":     [],
    })
    time.sleep(args.delay)

    # Run 1-3 boss encounters
    num_bosses = random.randint(1, 3)
    for _ in range(num_bosses):
        bt, bd = random.choice(BOSS_TYPES)
        simulate_encounter(client, bt, bd, args.delay)
        time.sleep(args.delay)


def main():
    args = parse_args()

    print("\n  BossSignal Test Harness")
    print(f"  Backend : {args.url}")
    print(f"  Secret  : {args.secret[:8]}…")

    # Verify backend is up
    try:
        r = requests.get(f"{args.url}/health", timeout=3)
        print(f"  Health  : HTTP {r.status_code} {r.json()}")
    except Exception as e:
        print(f"  ✗ Backend not responding at {args.url}")
        print(f"    {e}")
        print("  → Run: docker compose up -d   (from bosssignal-backend/)")
        sys.exit(1)

    print()

    if args.all_servers:
        server_ids = resolve_server_ids(args)
        print(f"  Servers : {', '.join(server_ids)}")
        print()
        for sid in server_ids:
            simulate_server(args.url, args.secret, sid, args)
            time.sleep(args.delay)
    else:
        simulate_server(args.url, args.secret, args.server, args)

    print(f"\n  ✓ Done. Open http://localhost:8080 to see the dashboard.")
    print()


if __name__ == "__main__":
    main()
