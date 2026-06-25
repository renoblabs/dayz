"""
Neo4j schema for DayZ modding memory graph.

Node types and relationship definitions that model the causal structure
of DayZ mod development errors, fixes, and patterns.
"""

# Node labels
DAYZ_ERROR = "DayZError"
ENFORCE_SCRIPT = "EnforceScript"
PBO_CONFIG = "PBOConfig"
WORKBENCH_STATE = "WorkbenchState"
TEST_SCENARIO = "TestScenario"
MOD_DEPENDENCY = "ModDependency"
SOLUTION = "Solution"
SESSION = "Session"

# Relationship types
CAUSES = "CAUSES"
TRIGGERS = "TRIGGERS"
SOLVES = "SOLVES"
OCCURS_IN = "OCCURS_IN"
DEPENDS_ON = "DEPENDS_ON"
REQUIRES = "REQUIRES"
TESTED_BY = "TESTED_BY"
DISCOVERED_IN = "DISCOVERED_IN"
EFFECTIVE_FOR = "EFFECTIVE_FOR"
PRECEDED_BY = "PRECEDED_BY"

# Constraint and index creation queries
SCHEMA_QUERIES = [
    # Unique constraints
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:DayZError) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:EnforceScript) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:PBOConfig) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Solution) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Session) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:ModDependency) REQUIRE n.name IS UNIQUE",

    # Full-text search indexes
    """CREATE FULLTEXT INDEX dayz_error_content IF NOT EXISTS
       FOR (n:DayZError) ON EACH [n.message, n.stack_trace, n.raw_snippet]""",
    """CREATE FULLTEXT INDEX solution_content IF NOT EXISTS
       FOR (n:Solution) ON EACH [n.description, n.code_change]""",
    """CREATE FULLTEXT INDEX enforce_content IF NOT EXISTS
       FOR (n:EnforceScript) ON EACH [n.pattern, n.description]""",
]


def init_schema(driver):
    """Initialize Neo4j schema with constraints and indexes."""
    with driver.session() as session:
        for query in SCHEMA_QUERIES:
            try:
                session.run(query)
            except Exception as e:
                # Constraints/indexes may already exist
                print(f"[schema] {e}")
