# src/nl_to_cypher.py
import re
from typing import Dict, Tuple

INTENT_PATTERNS = [
    # (intent_name, regex, slot_names)
    ("get_problem_difficulty", r"(?:题目|problem)\s*[\"']?([^\"']+)[\"']?\s*(?:的)?\s*(?:难度|rating)", ["problem"]),
    ("list_problems_by_tag", r"(?:有哪些|列出|给我).*?(?:关于|涉及|含有)\s*([^\s，。]+)", ["tag"]),
    ("get_contest_winner", r"(?:谁是|冠军|第一名).*(\d{4}|20\d{2}|[^\s，。]+赛)", ["year_or_name"]),
    ("get_team_by_contest_rank", r"(?:比赛|contest)\s*[\"']?([^\"']+)[\"']?.*?(?:第|rank)\s*(\d+)(?:名)?", ["contest_name", "rank"]),
    ("get_solutions_by_author", r"(?:作者|由)\s*([^\s，。]+)", ["author"]),
    ("find_problems_using_algorithm", r"(?:使用|用到|涉及)\s*([^\s，。]+)\s*(?:算法)?", ["algo"]),
    ("get_problem_info", r"(?:题目|problem)\s*[\"']?([^\"']+)[\"']?\s*(?:的)?\s*(?:信息|详情|是什么)?", ["problem"])
]

CYPHER_TEMPLATES = {
    "get_problem_difficulty":
        "MATCH (p:Problem) WHERE toLower(p.name) CONTAINS toLower($problem) RETURN p.name AS name, p.rating AS rating LIMIT 10",
    "list_problems_by_tag":
        "MATCH (p:Problem)-[:HAS_TAG]->(t:Tag) WHERE toLower(t.name)=toLower($tag) RETURN p.name AS name, p.rating AS rating LIMIT 100",
    "get_contest_winner":
        "MATCH (tm:Team)-[r:PLACED]->(c:Contest) WHERE toLower(c.name) CONTAINS toLower($year_or_name) AND (r.rank IN [1,'1','1st','冠军'] OR toString(r.rank) IN ['1','1st','冠军']) RETURN tm.name AS team, r.rank AS rank, r.region AS region LIMIT 5",
    "get_team_by_contest_rank":
        "MATCH (t:Team)-[r:PLACED]->(c:Contest) WHERE toLower(c.name) = toLower($contest_name) AND (r.rank = toInteger($rank) OR toString(r.rank) = $rank) RETURN t.name AS team_name, r.rank AS rank, r.region AS region LIMIT 1",
    "get_solutions_by_author":
        "MATCH (pr:Person {name:$author})<-[:AUTHOR]-(s:Solution)<-[:HAS_SOLUTION]-(p:Problem) RETURN p.name AS problem, s.id AS sid, substring(s.content,0,300) AS snippet LIMIT 50",
    "find_problems_using_algorithm":
        "MATCH (p:Problem)-[:HAS_TAG]->(t:Tag) WHERE toLower(t.name) CONTAINS toLower($algo) RETURN p.name AS name, p.rating AS rating LIMIT 100",
    "get_problem_info":
        "MATCH (p:Problem) WHERE toLower(p.name) CONTAINS toLower($problem) OPTIONAL MATCH (p)-[:HAS_TAG]->(t:Tag) OPTIONAL MATCH (p)-[:HAS_SOLUTION]->(s:Solution) RETURN p.name AS name, p.rating AS rating, collect(distinct t.name) AS tags, collect(distinct s.id) AS solutions LIMIT 5"
}

def parse_intent(question: str) -> Dict:
    q = question.strip()
    for intent, pattern, slots in INTENT_PATTERNS:
        m = re.search(pattern, q, re.I)
        if m:
            groups = m.groups()
            slot_values = {}
            for i, sname in enumerate(slots):
                slot_values[sname] = groups[i] if i < len(groups) and groups[i] is not None else ""
            return {"intent": intent, "slots": slot_values}
    return {"intent": "unknown", "slots": {}}

def get_cypher_and_params(intent_data: Dict) -> Tuple[str, Dict]:
    intent = intent_data.get("intent")
    slots = intent_data.get("slots", {})
    if intent in CYPHER_TEMPLATES:
        return CYPHER_TEMPLATES[intent], slots
    return "", {}
