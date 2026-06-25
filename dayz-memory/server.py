"""
DayZ Memory MCP Server - Graph-based knowledge system.

Stores errors, fixes, and patterns in Neo4j. Any AI IDE (Droid, Claude Code,
Cursor) can call these tools to read/write the shared memory graph.

Run:
    python -m dayz_memory.server

Requires:
    pip install fastmcp neo4j
    Neo4j running on bolt://localhost:7687
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    from fastmcp import FastMCP
except ImportError:
    print("Install fastmcp: pip install fastmcp")
    raise

try:
    from neo4j import GraphDatabase
except ImportError:
    print("Install neo4j driver: pip install neo4j")
    raise

from dayz_memory.schema import init_schema, CAUSES, SOLVES, OCCURS_IN, EFFECTIVE_FOR
from dayz_memory.models import DayZError, EnforceScript, Solution, Session

# Config from environment
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
# NEO4J_PASSWORD must be supplied via environment; the placeholder is not a usable default.
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "<your-neo4j-password>")
PROJECT_ID = os.environ.get("PROJECT_CONTEXT", "dayz-mod-<org>")

mcp = FastMCP("dayz-memory")

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        init_schema(_driver)
    return _driver


# ============================================================================
# Store Tools
# ============================================================================

@mcp.tool()
def store_error(
    message: str,
    error_type: str,
    mod_name: Optional[str] = None,
    file_location: Optional[str] = None,
    line_number: Optional[int] = None,
    stack_trace: str = "",
    raw_snippet: str = "",
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Store a DayZ error in the memory graph.

    Args:
        message: The error message
        error_type: One of: compile, runtime, load, conflict, hang
        mod_name: Which mod produced the error (e.g. HiveApiMod)
        file_location: File path where error occurred
        line_number: Line number of the error
        stack_trace: Full stack trace if available
        raw_snippet: Raw log snippet
        tags: Optional tags for categorization

    Returns:
        Dict with the stored error node ID
    """
    err = DayZError(
        message=message,
        error_type=error_type,
        mod_name=mod_name,
        file_location=file_location,
        line_number=line_number,
        stack_trace=stack_trace,
        raw_snippet=raw_snippet,
        tags=tags or [],
    )

    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            CREATE (e:DayZError $props)
            SET e.project = $project
            RETURN e.id AS id
            """,
            props=err.to_dict(),
            project=PROJECT_ID,
        )
        record = result.single()

    return {"status": "stored", "id": record["id"], "type": "DayZError"}


@mcp.tool()
def store_solution(
    description: str,
    error_id: str,
    code_change: str = "",
    file_path: Optional[str] = None,
    category: str = "",
) -> Dict[str, Any]:
    """
    Store a solution and link it to the error it fixes.

    Args:
        description: What the fix does
        error_id: ID of the DayZError this solves
        code_change: The actual code diff or change
        file_path: File that was modified
        category: One of: comment_out, replace, add, config

    Returns:
        Dict with solution ID and relationship created
    """
    sol = Solution(
        description=description,
        code_change=code_change,
        file_path=file_path,
        category=category,
    )

    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (e:DayZError {id: $error_id})
            CREATE (s:Solution $props)
            CREATE (s)-[:SOLVES]->(e)
            SET s.project = $project
            RETURN s.id AS id, e.message AS error_msg
            """,
            error_id=error_id,
            props=sol.to_dict(),
            project=PROJECT_ID,
        )
        record = result.single()

    if not record:
        return {"status": "error", "message": f"Error {error_id} not found"}

    return {
        "status": "stored",
        "id": record["id"],
        "type": "Solution",
        "linked_error": record["error_msg"],
    }


@mcp.tool()
def store_pattern(
    pattern: str,
    description: str,
    works: bool,
    file_path: Optional[str] = None,
    category: str = "",
) -> Dict[str, Any]:
    """
    Store an Enforce script pattern (working or broken).

    Args:
        pattern: The code pattern
        description: What it does / why it fails
        works: True if this pattern works in DayZ 1.29, False if broken
        file_path: Source file where this pattern lives
        category: One of: syntax, api, type, lifecycle

    Returns:
        Dict with pattern node ID
    """
    script = EnforceScript(
        pattern=pattern,
        description=description,
        works=works,
        file_path=file_path,
        category=category,
    )

    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            CREATE (p:EnforceScript $props)
            SET p.project = $project
            RETURN p.id AS id
            """,
            props=script.to_dict(),
            project=PROJECT_ID,
        )
        record = result.single()

    return {"status": "stored", "id": record["id"], "type": "EnforceScript", "works": works}


@mcp.tool()
def link_cause(source_id: str, target_id: str, relationship: str = "CAUSES") -> Dict[str, Any]:
    """
    Create a causal relationship between two nodes.

    Args:
        source_id: ID of the source node (the cause)
        target_id: ID of the target node (the effect)
        relationship: One of: CAUSES, TRIGGERS, PRECEDED_BY

    Returns:
        Dict confirming the relationship
    """
    valid_rels = {"CAUSES", "TRIGGERS", "PRECEDED_BY", "OCCURS_IN", "DEPENDS_ON", "REQUIRES"}
    if relationship not in valid_rels:
        return {"status": "error", "message": f"Invalid relationship. Use: {valid_rels}"}

    driver = get_driver()
    with driver.session() as session:
        # Use APOC-free approach: match by id property on any label
        query = f"""
            MATCH (a {{id: $source_id}})
            MATCH (b {{id: $target_id}})
            CREATE (a)-[r:{relationship}]->(b)
            RETURN type(r) AS rel, labels(a)[0] AS src_type, labels(b)[0] AS tgt_type
        """
        result = session.run(query, source_id=source_id, target_id=target_id)
        record = result.single()

    if not record:
        return {"status": "error", "message": "One or both nodes not found"}

    return {
        "status": "linked",
        "relationship": record["rel"],
        "from": record["src_type"],
        "to": record["tgt_type"],
    }


# ============================================================================
# Search Tools
# ============================================================================

@mcp.tool()
def search_errors(
    query: str,
    error_type: Optional[str] = None,
    mod_name: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Search for DayZ errors in the memory graph.

    Args:
        query: Text search query (searches message, stack_trace, raw_snippet)
        error_type: Filter by type: compile, runtime, load, conflict, hang
        mod_name: Filter by mod name
        resolved: Filter by resolved status
        limit: Max results to return

    Returns:
        Dict with matching errors and their linked solutions
    """
    driver = get_driver()
    with driver.session() as session:
        # Build dynamic WHERE clause
        where_parts = ["e.project = $project"]
        params = {"project": PROJECT_ID, "limit": limit}

        if error_type:
            where_parts.append("e.error_type = $error_type")
            params["error_type"] = error_type
        if mod_name:
            where_parts.append("e.mod_name = $mod_name")
            params["mod_name"] = mod_name
        if resolved is not None:
            where_parts.append("e.resolved = $resolved")
            params["resolved"] = resolved

        where_clause = " AND ".join(where_parts)

        # Full-text search if query provided
        if query and query.strip():
            cypher = f"""
                CALL db.index.fulltext.queryNodes('dayz_error_content', $query)
                YIELD node AS e, score
                WHERE {where_clause}
                OPTIONAL MATCH (s:Solution)-[:SOLVES]->(e)
                RETURN e, collect(s) AS solutions, score
                ORDER BY score DESC
                LIMIT $limit
            """
            params["query"] = query
        else:
            cypher = f"""
                MATCH (e:DayZError)
                WHERE {where_clause}
                OPTIONAL MATCH (s:Solution)-[:SOLVES]->(e)
                RETURN e, collect(s) AS solutions, 1.0 AS score
                ORDER BY e.timestamp DESC
                LIMIT $limit
            """

        result = session.run(cypher, **params)
        errors = []
        for record in result:
            node = dict(record["e"])
            solutions = [dict(s) for s in record["solutions"]]
            errors.append({
                "error": node,
                "solutions": solutions,
                "score": record["score"],
            })

    return {"status": "success", "count": len(errors), "results": errors}


@mcp.tool()
def find_similar_errors(error_message: str, limit: int = 5) -> Dict[str, Any]:
    """
    Find previously seen errors similar to the given message.
    Returns errors and their solutions ranked by similarity.

    Args:
        error_message: The error message to find matches for
        limit: Max results

    Returns:
        Dict with similar errors, their solutions, and effectiveness scores
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            CALL db.index.fulltext.queryNodes('dayz_error_content', $query)
            YIELD node AS e, score
            WHERE e.project = $project AND score > 0.5
            OPTIONAL MATCH (s:Solution)-[:SOLVES]->(e)
            RETURN e, collect(s) AS solutions, score
            ORDER BY score DESC
            LIMIT $limit
            """,
            query=error_message,
            project=PROJECT_ID,
            limit=limit,
        )

        matches = []
        for record in result:
            node = dict(record["e"])
            solutions = [dict(s) for s in record["solutions"]]
            best_fix = None
            if solutions:
                best_fix = max(solutions, key=lambda s: s.get("effectiveness") or 0)
            matches.append({
                "error": node,
                "similarity": record["score"],
                "solutions": solutions,
                "best_fix": best_fix,
            })

    return {"status": "success", "count": len(matches), "matches": matches}


@mcp.tool()
def get_causal_chain(error_id: str, depth: int = 3) -> Dict[str, Any]:
    """
    Traverse the causal graph to find root causes and downstream effects.

    Args:
        error_id: ID of the error node to start from
        depth: How many hops to traverse (1-5)

    Returns:
        Dict with upstream causes and downstream effects
    """
    depth = min(max(depth, 1), 5)
    driver = get_driver()
    with driver.session() as session:
        # Find upstream causes
        causes_result = session.run(
            f"""
            MATCH path = (cause)-[:CAUSES|TRIGGERS*1..{depth}]->(e:DayZError {{id: $id}})
            RETURN [n IN nodes(path) | {{id: n.id, type: labels(n)[0], message: n.message}}] AS chain
            """,
            id=error_id,
        )
        causes = [dict(r)["chain"] for r in causes_result]

        # Find downstream effects
        effects_result = session.run(
            f"""
            MATCH path = (e:DayZError {{id: $id}})-[:CAUSES|TRIGGERS*1..{depth}]->(effect)
            RETURN [n IN nodes(path) | {{id: n.id, type: labels(n)[0], message: n.message}}] AS chain
            """,
            id=error_id,
        )
        effects = [dict(r)["chain"] for r in effects_result]

    return {
        "status": "success",
        "error_id": error_id,
        "upstream_causes": causes,
        "downstream_effects": effects,
    }


# ============================================================================
# Effectiveness Tracking
# ============================================================================

@mcp.tool()
def track_fix_result(solution_id: str, worked: bool) -> Dict[str, Any]:
    """
    Record whether a solution worked when applied.
    Updates the effectiveness score automatically.

    Args:
        solution_id: ID of the Solution node
        worked: True if the fix resolved the error

    Returns:
        Dict with updated effectiveness score
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (s:Solution {id: $id})
            SET s.times_applied = COALESCE(s.times_applied, 0) + 1,
                s.times_succeeded = CASE WHEN $worked
                    THEN COALESCE(s.times_succeeded, 0) + 1
                    ELSE COALESCE(s.times_succeeded, 0) END,
                s.effectiveness = CASE WHEN (COALESCE(s.times_applied, 0) + 1) > 0
                    THEN toFloat(CASE WHEN $worked
                        THEN COALESCE(s.times_succeeded, 0) + 1
                        ELSE COALESCE(s.times_succeeded, 0) END)
                        / toFloat(COALESCE(s.times_applied, 0) + 1)
                    ELSE null END
            RETURN s.id AS id, s.effectiveness AS effectiveness,
                   s.times_applied AS applied, s.times_succeeded AS succeeded
            """,
            id=solution_id,
            worked=worked,
        )
        record = result.single()

    if not record:
        return {"status": "error", "message": f"Solution {solution_id} not found"}

    return {
        "status": "updated",
        "id": record["id"],
        "effectiveness": record["effectiveness"],
        "times_applied": record["applied"],
        "times_succeeded": record["succeeded"],
    }


@mcp.tool()
def get_top_solutions(error_type: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """
    Get the most effective solutions, ranked by success rate.

    Args:
        error_type: Filter by the error type they solve
        limit: Max results

    Returns:
        Ranked list of solutions with effectiveness scores
    """
    driver = get_driver()
    with driver.session() as session:
        where = "s.project = $project AND s.times_applied > 0"
        params = {"project": PROJECT_ID, "limit": limit}

        if error_type:
            where += " AND e.error_type = $error_type"
            params["error_type"] = error_type

        result = session.run(
            f"""
            MATCH (s:Solution)-[:SOLVES]->(e:DayZError)
            WHERE {where}
            RETURN s.id AS id, s.description AS description,
                   s.effectiveness AS effectiveness,
                   s.times_applied AS applied,
                   s.category AS category,
                   e.error_type AS error_type, e.message AS error_msg
            ORDER BY s.effectiveness DESC, s.times_applied DESC
            LIMIT $limit
            """,
            **params,
        )

        solutions = [dict(r) for r in result]

    return {"status": "success", "count": len(solutions), "solutions": solutions}


# ============================================================================
# Session Management
# ============================================================================

@mcp.tool()
def start_session(tool_name: str = "droid") -> Dict[str, Any]:
    """
    Start a new debugging session. Call this at the beginning of a conversation.

    Args:
        tool_name: Which AI IDE is being used (droid, claude_code, cursor)

    Returns:
        Dict with session ID and recent error context
    """
    sess = Session(tool_used=tool_name)
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            CREATE (s:Session $props)
            SET s.project = $project
            """,
            props=sess.to_dict(),
            project=PROJECT_ID,
        )

        # Get recent unresolved errors for context
        recent = session.run(
            """
            MATCH (e:DayZError {project: $project, resolved: false})
            OPTIONAL MATCH (s:Solution)-[:SOLVES]->(e)
            RETURN e.message AS message, e.error_type AS type,
                   e.mod_name AS mod, e.timestamp AS ts,
                   count(s) AS solution_count
            ORDER BY e.timestamp DESC
            LIMIT 5
            """,
            project=PROJECT_ID,
        )
        recent_errors = [dict(r) for r in recent]

    return {
        "status": "session_started",
        "session_id": sess.id,
        "tool": tool_name,
        "recent_unresolved_errors": recent_errors,
    }


@mcp.tool()
def get_stats() -> Dict[str, Any]:
    """
    Get statistics about the memory graph.

    Returns:
        Dict with counts of nodes, relationships, and effectiveness data
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (e:DayZError {project: $project})
            WITH count(e) AS errors,
                 count(CASE WHEN e.resolved THEN 1 END) AS resolved
            MATCH (s:Solution {project: $project})
            WITH errors, resolved, count(s) AS solutions,
                 avg(s.effectiveness) AS avg_effectiveness
            MATCH (p:EnforceScript {project: $project})
            WITH errors, resolved, solutions, avg_effectiveness,
                 count(p) AS patterns,
                 count(CASE WHEN p.works THEN 1 END) AS working_patterns
            RETURN errors, resolved, solutions, avg_effectiveness,
                   patterns, working_patterns
            """,
            project=PROJECT_ID,
        )
        record = result.single()

    if not record:
        return {"status": "empty", "message": "No data in graph yet"}

    return {
        "status": "success",
        "total_errors": record["errors"],
        "resolved_errors": record["resolved"],
        "solutions": record["solutions"],
        "avg_effectiveness": record["avg_effectiveness"],
        "patterns": record["patterns"],
        "working_patterns": record["working_patterns"],
    }


if __name__ == "__main__":
    mcp.run()
