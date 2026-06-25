"""Test: simulate an AI querying the graph when it encounters a new error."""
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

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:6703")
# NEO4J_PASSWORD must be supplied via environment; the placeholder is not a usable default.
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "<your-neo4j-password>")
driver = GraphDatabase.driver(NEO4J_URI, auth=("neo4j", NEO4J_PASSWORD))

print("=" * 60)
print("SCENARIO 1: AI encounters 'GetStamina' error")
print("=" * 60)

with driver.session() as session:
    result = session.run("""
        CALL db.index.fulltext.queryNodes('dayz_error_content', 'GetStamina')
        YIELD node AS e, score
        OPTIONAL MATCH (s:Solution)-[:SOLVES]->(e)
        RETURN e.message AS error, e.resolved AS resolved,
               s.description AS fix, s.effectiveness AS score,
               s.code_change AS code
        ORDER BY score DESC
        LIMIT 3
    """)
    for r in result:
        print(f"\n  Error: {r['error']}")
        print(f"  Resolved: {r['resolved']}")
        if r['fix']:
            eff = f"{r['score']:.0%}" if r['score'] else "unknown"
            print(f"  Fix [{eff} effective]: {r['fix']}")
            print(f"  Code: {r['code']}")

print("\n")
print("=" * 60)
print("SCENARIO 2: AI encounters 'server hangs on loading'")
print("=" * 60)

with driver.session() as session:
    result = session.run("""
        CALL db.index.fulltext.queryNodes('dayz_error_content', 'server hangs loading')
        YIELD node AS e, score
        OPTIONAL MATCH (s:Solution)-[:SOLVES]->(e)
        OPTIONAL MATCH (cause)-[:CAUSES]->(e)
        RETURN e.message AS error, e.resolved AS resolved,
               s.description AS fix, s.code_change AS code,
               cause.message AS root_cause
        ORDER BY score DESC
        LIMIT 3
    """)
    for r in result:
        print(f"\n  Error: {r['error']}")
        print(f"  Resolved: {r['resolved']}")
        if r['root_cause']:
            print(f"  Root Cause: {r['root_cause']}")
        if r['fix']:
            print(f"  Fix: {r['fix']}")
            print(f"  Code: {r['code']}")

print("\n")
print("=" * 60)
print("SCENARIO 3: AI checks 'code=7' connection failures")
print("=" * 60)

with driver.session() as session:
    result = session.run("""
        MATCH (e:DayZError)
        WHERE e.error_type = 'connection'
        RETURN e.message AS error, e.mod_name AS mod, e.timestamp AS ts
        ORDER BY e.timestamp DESC
        LIMIT 5
    """)
    for r in result:
        print(f"  [{r['mod']}] {r['error'][:70]}")

    # Check if we have a solution for connection errors
    result2 = session.run("""
        MATCH (s:Solution)-[:SOLVES]->(e:DayZError)
        WHERE e.error_type = 'connection'
        RETURN s.description AS fix
    """)
    fixes = [r['fix'] for r in result2]
    if fixes:
        print(f"\n  Known fix: {fixes[0]}")
    else:
        print(f"\n  No known fix yet - this is a NEW error type!")
        print(f"  -> Diagnosis: Backend APIs not running (ports 8080/8000)")
        print(f"  -> Fix: Start backends with modctl or uvicorn")

print("\n")
print("=" * 60)
print("SCENARIO 4: Show working vs broken patterns")
print("=" * 60)

with driver.session() as session:
    result = session.run("""
        MATCH (p:EnforceScript)
        RETURN p.pattern AS pattern, p.works AS works,
               p.description AS desc, p.category AS cat
        ORDER BY p.works ASC
    """)
    for r in result:
        status = "OK" if r['works'] else "BROKEN"
        print(f"  [{status}] [{r['cat']}] {r['desc'][:55]}")
        print(f"         {r['pattern'][:65]}")

driver.close()
print("\nAll queries completed successfully!")
