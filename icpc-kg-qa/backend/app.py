# backend/app.py
import os
from flask import Flask, request, jsonify, send_from_directory
from neo4j import GraphDatabase, basic_auth
from flask_cors import CORS  # pip install flask-cors

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# ---- Neo4j connection (example, keep your own creds) ----
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "luogu20201208")
driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASS))


def run_read(cypher, params=None):
    with driver.session() as session:
        result = session.run(cypher, params or {})
        return [dict(r.items()) for r in result]


# ---- Serve frontend index.html at root ----
@app.route("/")
def index():
    # static_folder="static"，所以会从 backend/static/index.html 查找
    return send_from_directory(app.static_folder, "index.html")


# Keep your existing API endpoints (parse/search/problem) here...
# For brevity, include the simple parse/search/problem examples:
KP_SYNONYMS = {
    # Binary Search
    "binary search": "Binary Search",
    "二分": "Binary Search",
    "二分查找": "Binary Search",

    # Shortest Path
    "shortest path": "Shortest Path",
    "最短路": "Shortest Path",
    "dijkstra": "Dijkstra",

    # Graph Theory
    # "graph": "Graph Theory",
    # "graph theory": "Graph Theory",
    "图论": "graphs",
}


@app.route("/api/parse", methods=["POST"])
def api_parse():
    data = request.json or {}
    query = data.get("query", "")
    candidates = []
    for token, kp in KP_SYNONYMS.items():
        if token in query.lower():
            candidates.append({"type": "KnowledgePoint", "name": kp, "score": 1.0})
    intent = "search_problems" if candidates else "unknown"
    return jsonify({"intent": intent, "candidates": candidates})


@app.route("/api/search", methods=["GET"])
def api_search():
    kp = request.args.get("k")
    limit = int(request.args.get("limit", 20))
    if not kp:
        return jsonify({"error": "missing parameter k (knowledge point)"}), 400
    cypher = """
    MATCH (p:Problem)-[:考察]->(k:KnowledgePoint)
    WHERE toLower(k.name) = toLower($kp)
    RETURN p.id AS id, p.title AS title, p.difficulty AS difficulty, p.source AS source
    LIMIT $limit
    """
    print(kp)
    rows = run_read(cypher, {"kp": kp, "limit": limit})
    print(rows)
    return jsonify({"results": rows, "total": len(rows)})


@app.route("/api/problem/<pid>", methods=["GET"])
def api_problem(pid):
    cypher_p = "MATCH (p:Problem {id:$pid}) RETURN p LIMIT 1"
    p_rows = run_read(cypher_p, {"pid": pid})
    if not p_rows:
        return jsonify({"error": "problem not found"}), 404
    cypher_paths = """
    MATCH path=(p:Problem {id:$pid})-[*1..3]-(x)
    WITH nodes(path) AS ns, relationships(path) AS rs
    WHERE ANY(n IN ns WHERE n:KnowledgePoint) AND ANY(n IN ns WHERE n:Algorithm)
    RETURN [n IN ns | {labels: labels(n), props: properties(n)}] AS nodes,
           [r IN rs | type(r)] AS rels
    LIMIT 10
    """
    paths = run_read(cypher_paths, {"pid": pid})
    return jsonify({"problem": p_rows[0]["p"], "paths": paths})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
