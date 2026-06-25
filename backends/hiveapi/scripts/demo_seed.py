#!/usr/bin/env python3
"""
Seed script that populates the database with sample fixture data.

This creates a sample scenario with multiple servers, players, and events
so the HiveAPI endpoints have data to return during local development.
All data here is synthetic/illustrative.
"""

import os
import sys
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.deps import SessionLocal
from app.db.models import Tenant, Cluster, Server, Player, Character, Event

# Synthetic sample data (fixtures) for local development
PLAYER_NAMES = [
    "HockeyPro_2024", "ZombieSlayer", "SurvivalExpert", "CanadianSniper",
    "GoalieKing", "RinkWarrior", "IceHunter", "PuckMaster", "StickWielder"
]

EVENT_TYPES = [
    "character_created", "character_claimed", "character_heartbeat",
    "inventory_updated", "inventory_set", "server_login"
]

ITEMS = [
    "HockeyStick", "BeerCan", "Jersey_Red", "Jersey_Blue", "GoalieMask",
    "Bandage", "Water", "Canned_Beans", "Backpack", "Knife"
]

def generate_rsa_keypair():
    """Generate RSA keypair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    return private_pem, public_pem


def create_realistic_demo_data(db: Session):
    """Create sample fixture data with multiple entities."""
    print("Creating sample fixture data for HiveAPI...\n")

    # Create tenant
    tenant_id = str(uuid.uuid4())
    tenant = Tenant(
        id=tenant_id,
        name="Hockey Apocalypse Network",
        owner_id="admin@hockeyapocalypse.com",
        settings_json={
            "description": "Multi-server DayZ cluster with hockey theme",
            "max_players": 100,
            "timezone": "America/Toronto"
        }
    )
    db.add(tenant)
    db.flush()
    print(f"✅ Created tenant: Hockey Apocalypse Network")

    # Create cluster
    cluster_id = str(uuid.uuid4())
    cluster = Cluster(
        id=cluster_id,
        tenant_id=tenant_id,
        name="North American Cluster",
        policy_json={
            "allow_transfer": True,
            "transfer_cooldown": 180,
            "max_inventory_size": 100
        }
    )
    db.add(cluster)
    db.flush()
    print(f"✅ Created cluster: North American Cluster")

    # Create multiple servers
    servers = []
    server_names = ["Toronto Rink", "Montreal Arena", "Vancouver Ice", "Chicago Stadium"]

    for server_name in server_names:
        private_pem, public_pem = generate_rsa_keypair()
        server_id = str(uuid.uuid4())

        server = Server(
            id=server_id,
            cluster_id=cluster_id,
            name=server_name,
            host_fingerprint=f"{server_name.lower().replace(' ', '-')}:fingerprint:{uuid.uuid4().hex[:8]}",
            public_key_pem=public_pem,
            status="active",
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            last_seen_at=datetime.utcnow() - timedelta(minutes=random.randint(1, 60))
        )
        db.add(server)
        db.flush()
        servers.append(server)

        # Save keys
        keys_dir = Path(__file__).parent.parent / "keys" / "servers"
        keys_dir.mkdir(parents=True, exist_ok=True)

        with open(keys_dir / f"{server_id}_private.pem", "w") as f:
            f.write(private_pem)

        print(f"   🖥️  Server: {server_name} ({server_id[:8]}...)")

    print(f"✅ Created {len(servers)} servers\n")

    # Create players and characters
    players = []
    characters = []

    for i, player_name in enumerate(PLAYER_NAMES):
        player_id = str(uuid.uuid4())
        steam_id = f"steam:7656119801{random.randint(100000, 999999)}"

        player = Player(
            id=player_id,
            platform_uid=steam_id,
            reputation=random.randint(-100, 500),
            meta={
                "nickname": player_name,
                "total_playtime": random.randint(10, 500),
                "kills": random.randint(0, 50),
                "deaths": random.randint(0, 20)
            },
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90)),
            last_seen_at=datetime.utcnow() - timedelta(hours=random.randint(0, 48))
        )
        db.add(player)
        db.flush()
        players.append(player)

        # Create 1-2 characters per player
        for j in range(random.randint(1, 2)):
            character_id = str(uuid.uuid4())
            owned_server = random.choice(servers)

            # Random inventory
            inventory = {
                "slots": {
                    str(k): {
                        "item": random.choice(ITEMS),
                        "quantity": random.randint(1, 5)
                    }
                    for k in range(random.randint(2, 8))
                }
            }

            character = Character(
                id=character_id,
                player_id=player_id,
                cluster_id=cluster_id,
                owned_by_server=owned_server.id,
                life_state=random.choice(["alive", "alive", "alive", "dead"]),
                position={
                    "x": random.uniform(0, 15000),
                    "y": random.uniform(0, 500),
                    "z": random.uniform(0, 15000)
                },
                stats_json={
                    "health": random.randint(50, 100),
                    "blood": random.randint(3000, 5000),
                    "water": random.randint(30, 100),
                    "energy": random.randint(30, 100)
                },
                inventory_json=inventory,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60)),
                last_seen_at=datetime.utcnow() - timedelta(hours=random.randint(0, 24))
            )
            db.add(character)
            db.flush()
            characters.append((character, owned_server))

    print(f"✅ Created {len(players)} players with {len(characters)} characters\n")

    # Create realistic events
    print("📊 Generating event history...")
    event_count = 0

    # Create events over the past 7 days
    for days_ago in range(7, 0, -1):
        base_time = datetime.utcnow() - timedelta(days=days_ago)

        # 5-20 events per day
        for _ in range(random.randint(5, 20)):
            event_time = base_time + timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            event_type = random.choice(EVENT_TYPES)
            character, server = random.choice(characters)

            payload = {}
            if event_type == "character_created":
                payload = {"position": character.position, "initial": True}
            elif event_type == "inventory_updated":
                payload = {
                    "items_added": random.randint(1, 5),
                    "items_removed": random.randint(0, 3)
                }
            elif event_type == "character_heartbeat":
                payload = {"health": random.randint(50, 100)}

            event = Event(
                id=str(uuid.uuid4()),
                type=event_type,
                actor=character.player_id if random.random() > 0.3 else None,
                object_id=character.id if random.random() > 0.2 else None,
                server_id=server.id,
                payload_json=payload,
                ts=event_time
            )
            db.add(event)
            event_count += 1

    db.flush()
    print(f"✅ Created {event_count} events across 7 days\n")

    # Commit everything
    db.commit()

    # Print summary
    print("=" * 60)
    print("SAMPLE DATA CREATED SUCCESSFULLY")
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   • Tenant:     Hockey Apocalypse Network")
    print(f"   • Cluster:    North American Cluster")
    print(f"   • Servers:    {len(servers)} servers")
    print(f"   • Players:    {len(players)} players")
    print(f"   • Characters: {len(characters)} characters")
    print(f"   • Events:     {event_count} events")

    print(f"\n🔑 Test Credentials:")
    print(f"   Tenant ID:  {tenant_id}")
    print(f"   Cluster ID: {cluster_id}")

    print(f"\n🖥️  Servers:")
    for server in servers:
        print(f"   • {server.name:20} {server.id}")

    print(f"\n👥 Sample Players:")
    for player in players[:3]:
        print(f"   • {player.meta.get('nickname', 'Unknown'):20} {player.platform_uid}")

    print(f"\n🚀 Quick Test:")
    print(f"   # Login as first server:")
    print(f"   curl -X POST http://localhost:8000/v1/auth/server-login \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"server_id\":\"{servers[0].id}\"}}'")

    print(f"\n   # View overview:")
    print(f"   curl http://localhost:8000/v1/admin/overview")

    print(f"\n   # View events:")
    print(f"   curl http://localhost:8000/v1/admin/events?limit=10")

    print(f"\n✨ Open the Web UI at http://localhost:3000 to see it all!")
    print("=" * 60)


def main():
    """Main entry point."""
    db = SessionLocal()
    try:
        create_realistic_demo_data(db)
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating demo data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
