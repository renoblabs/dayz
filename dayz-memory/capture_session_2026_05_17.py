"""
Capture the 2026-05-17 troubleshooting session's 4 bugs into the Neo4j memory graph.

Idempotent: every node is MERGEd on a stable key (error_signature / name / path),
so re-running this script never creates duplicates — the anti-pollution invariant
the whole capture loop depends on.

Run:  C:\\Users\\<user>\\Dayz\\dayz\\platform\\.venv\\Scripts\\python.exe \
      C:\\Users\\<user>\\Dayz\\dayz\\dayz-memory\\capture_session_2026_05_17.py

Schema follows seed.py: (:DayZError)<-[:SOLVES]-(:Solution), plus the structured
fields requested for the learning loop (error_signature, root_cause, fix_applied,
resolution_status, related_files, session_id) and (:DayZError)-[:RELATED_TO_MOD]->
(:ModDependency) / -[:RELATED_TO_FILE]->(:File).
"""

import os
from datetime import datetime, timezone

from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:6703")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
# NEO4J_PASSWORD must be supplied via environment; the placeholder below is not a
# usable default — set NEO4J_PASSWORD to your own Neo4j password before running.
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "<your-neo4j-password>")
PROJECT = "dayz-mod-<org>"
SESSION_ID = "2026-05-17-troubleshoot"
TS = datetime.now(timezone.utc).isoformat()
DOC = "planning/in-game-test-troubleshoot-2026-05-17.md"

# Each bug: the DayZError fields (seed-compatible) + the structured learning-loop
# fields + its Solution + the mods/files it relates to.
BUGS = [
    {
        "error_signature": "0x00040074-client-mods-under-server-tree",
        "message": "VE_UNEXPECTED_MOD_PBO 0x00040074 — client preset mounts @BossSignal/@TrophyHunter under the DAYZSERVER tree",
        "error_type": "conflict",
        "mod_name": "BossSignal",
        "root_cause": "DayZ Launcher preset dayz.defaultpreset2 had local: entries resolving into C:\\...\\DAYZSERVER\\@BossSignal\\ and \\@TrophyHunter\\. The modlist handshake registers mount path as module identity; client mounting from the server's own tree != server mount -> kick even with byte-identical PBOs.",
        "fix_applied": "Decision: use launcher 'SETUP DLCS AND MODS AND JOIN' against the live server (auto-matches modset) instead of hand-editing the preset. Corrected preset XML drafted but NOT written.",
        "resolution_status": "resolved",
        "resolved": True,
        "related_files": [DOC, "%LOCALAPPDATA%\\DayZ Launcher\\Presets\\dayz.defaultpreset2"],
        "mods": ["BossSignal", "TrophyHunter"],
        "solution": "Never point a client local-mod entry into the DAYZSERVER install tree; use the client !Workshop tree, or let SETUP DLCS AND MODS AND JOIN resolve the modset from the live server.",
        "solution_category": "config",
    },
    {
        "error_signature": "0x00040074-extra-namalsk-mods-in-preset",
        "message": "VE_UNEXPECTED_MOD_PBO 0x00040074 — client preset carried Namalsk + 5 extra mods the server does not run",
        "error_type": "conflict",
        "mod_name": None,
        "root_cause": "Preset included Namalsk Survival/Island + Code Lock + NMP + VanillaPlusPlusMap + LibBSH (subscribed from an external favourites list). The target server runs a smaller modset. Composition mismatch -> kick. Tell-tale: nst/namalsk/...mainmenu.c in the client RPT next to the 0x00040074 throw.",
        "fix_applied": "SETUP DLCS AND MODS AND JOIN applies the server's exact modlist, dropping the extras.",
        "resolution_status": "resolved",
        "resolved": True,
        "related_files": [DOC, "%LOCALAPPDATA%\\DayZ\\DayZ_x64_2026-05-17_21-35-08.RPT"],
        "mods": ["Namalsk Survival", "Namalsk Island"],
        "solution": "Grep newest client RPT for '0x00040074|LoadMods|nst/namalsk' — a non-server mod's source path beside a 0x000 throw means composition mismatch; strip extras via SETUP DLCS.",
        "solution_category": "config",
    },
    {
        "error_signature": "0x00040074-bosscontentmod-missing-from-preset",
        "message": "VE_UNEXPECTED_MOD_PBO 0x00040074 — @BossContentMod (steam:YOUR_BOSS_MOD_ID) absent from client preset though server requires it",
        "error_type": "conflict",
        "mod_name": "BossContentMod",
        "root_cause": "12-entry preset had no steam:YOUR_BOSS_MOD_ID, but launch_modded.bat requires @BossContentMod at -mod chain pos 3. The error parenthetical even named @BossContentMod\\addons\\BossContentMod.pbo as the boundary.",
        "fix_applied": "SETUP DLCS AND MODS AND JOIN pulls the full required modset incl. BossContentMod from the live server.",
        "resolution_status": "resolved",
        "resolved": True,
        "related_files": [DOC, "%DAYZ_SERVER_PATH%\\launch_modded.bat"],
        "mods": ["BossContentMod"],
        "solution": "Diff preset published-ids against `grep -oE '@\\w+' launch_modded.bat`; any server mod with no matching preset id is a missing-required-mod bug.",
        "solution_category": "config",
    },
    {
        "error_signature": "vpp-menu-unbound-keybind-not-auth",
        "message": "VPP Admin Tools menu unresponsive to all keys for a confirmed Super Admin",
        "error_type": "runtime",
        "mod_name": "VPPAdminTools",
        "root_cause": "NOT an auth bug. SuperAdmins.txt correct (clean LF, ID present) and VPP boot log shows '[PermissionManager] Adding Super Admin (<your-steam64-id>)'. Real cause: VPP Admin Tools ships with NO default menu keybind; the open-menu action must be bound client-side in DayZ Options -> Controls.",
        "fix_applied": "Client-side only: bind the VPP menu action in Options -> Controls. No server file edited, no restart (would have been wrong + risked the live connection).",
        "resolution_status": "client_action_pending",
        "resolved": False,
        "related_files": [DOC, "profiles/VPPAdminTools/Permissions/SuperAdmins/SuperAdmins.txt", "profiles/VPPAdminTools/Logging/Log_2026-5-17_23-34-20.txt"],
        "mods": ["VPPAdminTools"],
        "solution": "Verify SuperAdmins.txt + grep VPP log for 'Adding Super Admin'. If both green, it is the unbound client keybind — bind it in Options -> Controls. Do NOT edit permission files or restart the server.",
        "solution_category": "config",
    },
]

CYPHER = """
MERGE (e:DayZError {error_signature: $error_signature})
SET e.message = $message,
    e.error_type = $error_type,
    e.mod_name = $mod_name,
    e.root_cause = $root_cause,
    e.fix_applied = $fix_applied,
    e.resolution_status = $resolution_status,
    e.resolved = $resolved,
    e.related_files = $related_files,
    e.session_id = $session_id,
    e.timestamp = $timestamp,
    e.project = $project,
    e.troubleshoot_doc = $doc
MERGE (s:Solution {description: $solution})
SET s.category = $solution_category,
    s.project = $project,
    s.session_id = $session_id,
    s.timestamp = $timestamp
MERGE (s)-[:SOLVES]->(e)
WITH e
UNWIND $mods AS mod_name
  MERGE (m:ModDependency {name: mod_name})
  MERGE (e)-[:RELATED_TO_MOD]->(m)
WITH e
UNWIND $related_files AS fpath
  MERGE (f:File {path: fpath})
  MERGE (e)-[:RELATED_TO_FILE]->(f)
"""


def main() -> None:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        for b in BUGS:
            session.run(
                CYPHER,
                error_signature=b["error_signature"],
                message=b["message"],
                error_type=b["error_type"],
                mod_name=b["mod_name"],
                root_cause=b["root_cause"],
                fix_applied=b["fix_applied"],
                resolution_status=b["resolution_status"],
                resolved=b["resolved"],
                related_files=b["related_files"],
                session_id=SESSION_ID,
                timestamp=TS,
                project=PROJECT,
                doc=DOC,
                solution=b["solution"],
                solution_category=b["solution_category"],
                mods=b["mods"],
            )
        # Report what is now queryable for this session
        rows = session.run(
            """
            MATCH (e:DayZError {session_id: $sid})
            OPTIONAL MATCH (s:Solution)-[:SOLVES]->(e)
            RETURN e.error_signature AS sig, e.resolution_status AS status,
                   count(s) AS solutions
            ORDER BY sig
            """,
            sid=SESSION_ID,
        )
        captured = list(rows)
    driver.close()
    print(f"[capture] session {SESSION_ID}: {len(captured)} bugs in graph (idempotent MERGE)")
    for r in captured:
        print(f"  - {r['sig']:<45} status={r['status']:<22} solutions={r['solutions']}")


if __name__ == "__main__":
    main()
