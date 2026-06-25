"""Test script: capture live errors from DayZ server logs into Neo4j."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import importlib.util
for name, fname in [('dayz_memory','__init__.py'),('dayz_memory.schema','schema.py'),('dayz_memory.models','models.py')]:
    fpath = os.path.join(os.path.dirname(__file__), fname)
    spec = importlib.util.spec_from_file_location(
        name, fpath,
        submodule_search_locations=[os.path.dirname(__file__)] if name == 'dayz_memory' else None
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)

from neo4j import GraphDatabase
from dayz_memory.models import DayZError

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:6703")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
# NEO4J_PASSWORD must be supplied via environment; the placeholder is not a usable default.
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "<your-neo4j-password>")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Read live server log. Point DAYZ_SERVER_PATH at your DayZ server install root.
dayz_server_path = os.environ.get(
    "DAYZ_SERVER_PATH",
    r"C:\Program Files (x86)\Steam\steamapps\common\DayZServer",
)
log_dir = os.path.join(dayz_server_path, "profiles")
logs = sorted([f for f in os.listdir(log_dir) if f.startswith("script_")], reverse=True)
content = open(os.path.join(log_dir, logs[0]), "r").read()

errors_found = [line.strip() for line in content.split("\n") if "ERROR" in line or "FAIL" in line]
print(f"Found {len(errors_found)} error lines in live log: {logs[0]}")

stored = 0
seen = set()
with driver.session() as session:
    for line in errors_found:
        key = line[:80]
        if key in seen:
            continue
        seen.add(key)

        etype = "runtime"
        mod_name = None
        if "BossSignal" in line:
            mod_name = "BossSignal"
        elif "HiveAPI" in line:
            mod_name = "HiveApiMod"
        elif "TrophyHunter" in line:
            mod_name = "TrophyHunter"

        if "compile" in line.lower():
            etype = "compile"
        elif "code=7" in line:
            etype = "connection"

        err = DayZError(message=line, error_type=etype, mod_name=mod_name, tags=["live", "auto-captured"])
        session.run(
            "CREATE (e:DayZError $props) SET e.project = $project",
            props=err.to_dict(),
            project="dayz-mod-<org>",
        )
        stored += 1
        print(f"  Stored: {line[:80]}...")

print(f"\nStored {stored} unique errors from live log")

# Now query the graph to show what we have
print("\n--- Graph Stats ---")
with driver.session() as session:
    result = session.run("""
        MATCH (n)
        RETURN labels(n)[0] AS type, count(n) AS count
        ORDER BY count DESC
    """)
    for r in result:
        print(f"  {r['type']}: {r['count']} nodes")

    print("\n--- Solutions with effectiveness ---")
    result = session.run("""
        MATCH (s:Solution)-[:SOLVES]->(e:DayZError)
        RETURN s.description AS fix, s.effectiveness AS score,
               s.times_applied AS applied, e.message AS error
        ORDER BY s.effectiveness DESC
    """)
    for r in result:
        eff = f"{r['score']:.0%}" if r['score'] else "?"
        print(f"  [{eff}] {r['fix'][:60]}")
        print(f"         -> fixes: {r['error'][:60]}")

    print("\n--- Causal Chains ---")
    result = session.run("""
        MATCH (a)-[r:CAUSES]->(b)
        RETURN a.message AS cause, b.message AS effect
    """)
    for r in result:
        print(f"  {r['cause'][:50]}...")
        print(f"    CAUSES -> {r['effect'][:50]}...")

driver.close()
