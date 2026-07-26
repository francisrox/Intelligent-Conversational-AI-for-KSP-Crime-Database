import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "ksp_graph_pass")

_driver = None


def get_driver():
    """Reuse a single driver instance (it manages its own connection pool)
    instead of opening a new connection per request."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def run_cypher(query: str, parameters: dict = None):
    """Returns raw Neo4j Record objects — NOT .data()-converted.

    Deliberately NOT calling .data() here: it recursively flattens Nodes/Paths/
    Relationships into plain dicts/lists, which destroys the .labels/.nodes/
    .relationships structure that graph-traversal queries (e.g. get_accused_network)
    need. Callers that only ever SELECT scalar fields (ids, names, counts) can
    safely do dict(record) themselves — callers that return whole nodes/paths
    need the real graph objects."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, parameters or {})
        return list(result)
