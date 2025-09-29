# src/neo4j_helper.py
from neo4j import GraphDatabase
from typing import List, Dict, Any

class Neo4jHelper:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", pwd="luogu20201208"):
        self.driver = GraphDatabase.driver(uri, auth=(user, pwd))

    def run_query(self, cypher: str, params: Dict = None) -> List[Dict[str, Any]]:
        params = params or {}
        with self.driver.session() as session:
            res = session.run(cypher, **params)
            return [dict(record) for record in res]

    def close(self):
        self.driver.close()
