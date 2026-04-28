"""
Neo4j Schema — Cypher queries for index creation and schema management.

Called by Neo4jStorage._ensure_schema() to set up vector + fulltext indexes.
Vector dimensions are configurable (auto-detected from embedding model).
"""

# Constraints
CREATE_GRAPH_UUID_CONSTRAINT = """
CREATE CONSTRAINT graph_uuid IF NOT EXISTS
FOR (g:Graph) REQUIRE g.graph_id IS UNIQUE
"""

CREATE_ENTITY_UUID_CONSTRAINT = """
CREATE CONSTRAINT entity_uuid IF NOT EXISTS
FOR (n:Entity) REQUIRE n.uuid IS UNIQUE
"""

CREATE_EPISODE_UUID_CONSTRAINT = """
CREATE CONSTRAINT episode_uuid IF NOT EXISTS
FOR (ep:Episode) REQUIRE ep.uuid IS UNIQUE
"""

# Fulltext indexes (for BM25 keyword search)
CREATE_ENTITY_FULLTEXT_INDEX = """
CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS
FOR (n:Entity) ON EACH [n.name, n.summary]
"""

CREATE_FACT_FULLTEXT_INDEX = """
CREATE FULLTEXT INDEX fact_fulltext IF NOT EXISTS
FOR ()-[r:RELATION]-() ON EACH [r.fact, r.name]
"""

# Static schema queries (constraints + fulltext — dimension-independent)
STATIC_SCHEMA_QUERIES = [
    CREATE_GRAPH_UUID_CONSTRAINT,
    CREATE_ENTITY_UUID_CONSTRAINT,
    CREATE_EPISODE_UUID_CONSTRAINT,
    CREATE_ENTITY_FULLTEXT_INDEX,
    CREATE_FACT_FULLTEXT_INDEX,
]


def get_vector_index_queries(dimensions: int) -> list:
    """Return vector index creation queries for the given dimension."""
    return [
        f"""CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
FOR (n:Entity) ON (n.embedding)
OPTIONS {{indexConfig: {{
    `vector.dimensions`: {dimensions},
    `vector.similarity_function`: 'cosine'
}}}}""",
        f"""CREATE VECTOR INDEX fact_embedding IF NOT EXISTS
FOR ()-[r:RELATION]-() ON (r.fact_embedding)
OPTIONS {{indexConfig: {{
    `vector.dimensions`: {dimensions},
    `vector.similarity_function`: 'cosine'
}}}}""",
    ]
