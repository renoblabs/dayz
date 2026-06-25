"""
Seed the memory graph with known DayZ 1.29 issues discovered during this session.

Run: python -m dayz_memory.seed
"""

import os
from neo4j import GraphDatabase
from dayz_memory.schema import init_schema
from dayz_memory.models import DayZError, EnforceScript, Solution

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
# NEO4J_PASSWORD must be supplied via environment; the placeholder is not a usable default.
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "<your-neo4j-password>")
PROJECT = "dayz-mod-<org>"


def seed():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    init_schema(driver)

    with driver.session() as session:
        # Error 1: GetStamina removed
        e1 = DayZError(
            message="Undefined function 'PlayerBase.GetStamina'",
            error_type="compile",
            mod_name="HiveApiMod",
            file_location="HiveApiMod/scripts/5_mission/HiveApiCharacterSync.c",
            line_number=111,
            dayz_version="1.29",
            resolved=True,
            tags=["enforce", "api_removed", "1.29"],
        )
        session.run(
            "CREATE (e:DayZError $props) SET e.project = $project",
            props=e1.to_dict(), project=PROJECT,
        )

        s1 = Solution(
            description="Comment out player.GetStamina() - function removed in DayZ 1.29",
            code_change='// stats.Set("stamina", player.GetStamina());',
            file_path="mods/HiveApiMod/scripts/5_mission/HiveApiCharacterSync.c",
            category="comment_out",
            effectiveness=1.0,
            times_applied=3,
            times_succeeded=3,
        )
        session.run(
            """
            MATCH (e:DayZError {message: $msg})
            CREATE (s:Solution $props)
            CREATE (s)-[:SOLVES]->(e)
            SET s.project = $project
            """,
            msg=e1.message, props=s1.to_dict(), project=PROJECT,
        )

        # Error 2: Param2 class missing
        e2 = DayZError(
            message="Bad type 'Param2' / Can't find class Param2",
            error_type="compile",
            mod_name="HiveApiMod",
            file_location="HiveApiMod/scripts/5_mission/HiveApiCharacterSync.c",
            line_number=162,
            dayz_version="1.29",
            resolved=True,
            tags=["enforce", "type_changed", "1.29"],
        )
        session.run(
            "CREATE (e:DayZError $props) SET e.project = $project",
            props=e2.to_dict(), project=PROJECT,
        )

        s2 = Solution(
            description="Comment out Param2 usage - template class changed in DayZ 1.29",
            code_change="// timer.Run(..., new Param2<string, PlayerBase>(...), true);",
            file_path="mods/HiveApiMod/scripts/5_mission/HiveApiCharacterSync.c",
            category="comment_out",
            effectiveness=1.0,
            times_applied=3,
            times_succeeded=3,
        )
        session.run(
            """
            MATCH (e:DayZError {message: $msg})
            CREATE (s:Solution $props)
            CREATE (s)-[:SOLVES]->(e)
            SET s.project = $project
            """,
            msg=e2.message, props=s2.to_dict(), project=PROJECT,
        )

        # Error 3: HTTP call blocks world load
        e3 = DayZError(
            message="Server hangs on world loading at Land_Mil_Barracks1",
            error_type="hang",
            mod_name="HiveApiMod",
            file_location="HiveApiMod/scripts/5_mission/HiveApiCharacterSync.c",
            dayz_version="1.29",
            resolved=True,
            tags=["http", "blocking", "onInit", "world_load"],
        )
        session.run(
            "CREATE (e:DayZError $props) SET e.project = $project",
            props=e3.to_dict(), project=PROJECT,
        )

        s3 = Solution(
            description="Defer HTTP calls with CallLater(10000ms) to prevent blocking world load",
            code_change="GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(HiveApiClient.ServerLogin, 10000, false, HiveApiConfig.SERVER_ID);",
            file_path="mods/HiveApiMod/scripts/5_mission/HiveApiCharacterSync.c",
            category="replace",
            effectiveness=1.0,
            times_applied=2,
            times_succeeded=2,
        )
        session.run(
            """
            MATCH (e:DayZError {message: $msg})
            CREATE (s:Solution $props)
            CREATE (s)-[:SOLVES]->(e)
            SET s.project = $project
            """,
            msg=e3.message, props=s3.to_dict(), project=PROJECT,
        )

        # Error 4: $mpmissions path alias
        e4 = DayZError(
            message="Failed to load $mpmissions:TrophyHunter/bosses.json",
            error_type="load",
            mod_name="TrophyHunter",
            file_location="TrophyHunter/scripts/3_game/TrophyHunterConfig.c",
            dayz_version="1.29",
            resolved=True,
            tags=["path_alias", "config", "jsonfileloader"],
        )
        session.run(
            "CREATE (e:DayZError $props) SET e.project = $project",
            props=e4.to_dict(), project=PROJECT,
        )

        s4 = Solution(
            description="Use $mission: instead of $mpmissions: for current mission folder",
            code_change='static string BOSSES_JSON_PATH = "$mission:TrophyHunter/bosses.json";',
            file_path="mods/TrophyHunter/scripts/3_game/TrophyHunterConfig.c",
            category="replace",
            effectiveness=1.0,
            times_applied=1,
            times_succeeded=1,
        )
        session.run(
            """
            MATCH (e:DayZError {message: $msg})
            CREATE (s:Solution $props)
            CREATE (s)-[:SOLVES]->(e)
            SET s.project = $project
            """,
            msg=e4.message, props=s4.to_dict(), project=PROJECT,
        )

        # Error 5: PBO not rebuilding (cached)
        e5 = DayZError(
            message="Rebuilt PBO still contains old code after source edit",
            error_type="load",
            mod_name="TrophyHunter",
            dayz_version="1.29",
            resolved=True,
            tags=["filebank", "cache", "pbo", "build"],
        )
        session.run(
            "CREATE (e:DayZError $props) SET e.project = $project",
            props=e5.to_dict(), project=PROJECT,
        )

        s5 = Solution(
            description="Stop server, delete old PBO, rebuild. FileBank won't overwrite locked files.",
            code_change="Stop-Process DayZServer_x64; Remove-Item output/@Mod/addons/*.pbo; modctl build mod",
            category="config",
            effectiveness=1.0,
            times_applied=2,
            times_succeeded=2,
        )
        session.run(
            """
            MATCH (e:DayZError {message: $msg})
            CREATE (s:Solution $props)
            CREATE (s)-[:SOLVES]->(e)
            SET s.project = $project
            """,
            msg=e5.message, props=s5.to_dict(), project=PROJECT,
        )

        # Causal chain: GetStamina -> compile fail -> server crash
        session.run(
            """
            MATCH (e1:DayZError {message: $msg1})
            MATCH (e3:DayZError {message: $msg3})
            CREATE (e1)-[:CAUSES]->(e3)
            """,
            msg1=e1.message, msg3=e3.message,
        )

        # Working patterns
        patterns = [
            EnforceScript(
                pattern='GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(fn, delay, false, arg)',
                description="Deferred function call - safe for OnInit HTTP requests",
                works=True,
                category="lifecycle",
            ),
            EnforceScript(
                pattern='player.GetHealth("", "Health")',
                description="Get player health - works in 1.29 (unlike GetStamina)",
                works=True,
                category="api",
            ),
            EnforceScript(
                pattern='player.GetStamina()',
                description="REMOVED in DayZ 1.29 - use GetStaminaHandler() or omit",
                works=False,
                category="api",
            ),
            EnforceScript(
                pattern='new Param2<TypeA, TypeB>(a, b)',
                description="Param2 template class broken in DayZ 1.29",
                works=False,
                category="type",
            ),
            EnforceScript(
                pattern='JsonFileLoader<ref MyClass>.LoadFile(path, data, errMsg)',
                description="JSON file loading - use ref keyword in type parameter",
                works=True,
                category="api",
            ),
        ]

        for p in patterns:
            session.run(
                "CREATE (p:EnforceScript $props) SET p.project = $project",
                props=p.to_dict(), project=PROJECT,
            )

    driver.close()
    print(f"[seed] Seeded {PROJECT} with 5 errors, 5 solutions, 5 patterns, 1 causal link")


if __name__ == "__main__":
    seed()
