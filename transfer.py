import pandas as pd
import hashlib
import re
import os


def short_id(prefix: str, key: str, length: int = 8):
    h = hashlib.md5(key.encode('utf-8')).hexdigest()[:length]
    return f"{prefix}_{h}"


def split_tags(tag_str):
    if pd.isna(tag_str):
        return []
    # 常见分隔符：, ; / | 空格
    parts = re.split(r'[;,/|]+|\s{2,}|\s*,\s*', str(tag_str))
    res = []
    for p in parts:
        p = p.strip()
        if p:
            res.append(p)
    return list(dict.fromkeys(res))  # 保持顺序并去重


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


# ---------- load input CSVs ----------
problems_df = pd.read_csv("problems.csv", dtype=str).fillna("")
contests_df = pd.read_csv("contest.csv", dtype=str).fillna("")
solutions_df = pd.read_csv("solution.csv", dtype=str).fillna("")

# ---------- normalize column names (小写) ----------
problems_df.columns = [c.strip() for c in problems_df.columns]
contests_df.columns = [c.strip() for c in contests_df.columns]
solutions_df.columns = [c.strip() for c in solutions_df.columns]

# ---------- containers for unique nodes ----------
tags_map = {}  # tag_name -> tag_id
contests_map = {}  # contest_name -> contest_id
teams_map = {}  # team_name -> team_id
persons_map = {}  # person_name -> person_id
problems_nodes = []  # dicts
solutions_nodes = []  # dicts

problem_tag_rels = []
problem_contest_rels = []
problem_solution_rels = []

for idx, row in problems_df.iterrows():
    pname = str(row.get("name", "")).strip()
    if not pname:
        continue
    pkey = pname + "|" + str(row.get("from", "")).strip()
    pid = short_id("P", pkey)
    rating = row.get("rating", "").strip()
    source = row.get("from", "").strip()
    raw_solution_field = row.get("solution", "").strip()

    problems_nodes.append({
        "id": pid,
        "name": pname,
        "rating": rating,
        "source": source,
        "raw_solution_field": raw_solution_field
    })

    raw_tags = row.get("tags", "")
    tags = split_tags(raw_tags)
    for t in tags:
        if t not in tags_map:
            tags_map[t] = short_id("T", t)
        problem_tag_rels.append({"problem_id": pid, "tag_id": tags_map[t]})

    if source:
        cname = source
        if cname not in contests_map:
            contests_map[cname] = short_id("C", cname)
        problem_contest_rels.append({"problem_id": pid, "contest_id": contests_map[cname]})

    if raw_solution_field:
        sol_ids = re.split(r'[;,|]+|\s+', raw_solution_field.strip())
        sol_ids = [s.strip() for s in sol_ids if s.strip()]
        for sid in sol_ids:
            problem_solution_rels.append({"problem_id": pid, "solution_id": sid})

team_contest_rels = []
for idx, row in contests_df.iterrows():
    cname = str(row.get("name", "")).strip()
    teamname = str(row.get("team", "")).strip()
    rank = str(row.get("rank", "")).strip()
    region = str(row.get("region", "")).strip()

    if not cname or not teamname:
        continue
    if cname not in contests_map:
        contests_map[cname] = short_id("C", cname)
    cid = contests_map[cname]

    if teamname not in teams_map:
        teams_map[teamname] = short_id("TEAM", teamname)
    tid = teams_map[teamname]

    team_contest_rels.append({
        "team_id": tid,
        "team_name": teamname,
        "contest_id": cid,
        "contest_name": cname,
        "rank": rank,
        "region": region
    })

solution_author_rels = []

for idx, row in solutions_df.iterrows():
    sid = str(row.get("id", "")).strip()
    if not sid:
        # 如果没有 id，生成一个基于 content 的 id
        sid = short_id("S", str(row.get("content", "")) + str(idx))
    writer = str(row.get("writer", "")).strip()
    content = str(row.get("content", "")).strip()

    solutions_nodes.append({
        "id": sid,
        "writer": writer,
        "content": content
    })

    if writer:
        if writer not in persons_map:
            persons_map[writer] = short_id("PERSON", writer)
        pidr = persons_map[writer]
        solution_author_rels.append({"solution_id": sid, "person_id": pidr})

tags_nodes = [{"id": tid, "name": name} for name, tid in tags_map.items()]
contests_nodes = [{"id": cid, "name": name} for name, cid in contests_map.items()]
teams_nodes = [{"id": tid, "name": name} for name, tid in teams_map.items()]
persons_nodes = [{"id": pid, "name": name} for name, pid in persons_map.items()]

out_dir = "neo4j_import_csvs"
ensure_dir(out_dir)


def df_to_csv(lst, fname):
    df = pd.DataFrame(lst)

    df.to_csv(os.path.join(out_dir, fname), index=False, encoding="utf-8-sig", quoting=1)  # quoting=1 -> csv.QUOTE_ALL


df_to_csv(problems_nodes, "problems_nodes.csv")
df_to_csv(tags_nodes, "tags_nodes.csv")
df_to_csv(contests_nodes, "contests_nodes.csv")
df_to_csv(teams_nodes, "teams_nodes.csv")
df_to_csv(persons_nodes, "persons_nodes.csv")
df_to_csv(solutions_nodes, "solutions_nodes.csv")

df_to_csv(problem_tag_rels, "problem_tag_rels.csv")
df_to_csv(problem_contest_rels, "problem_contest_rels.csv")
df_to_csv(problem_solution_rels, "problem_solution_rels.csv")
df_to_csv(solution_author_rels, "solution_author_rels.csv")
df_to_csv(team_contest_rels, "team_contest_rels.csv")

print("Done. CSVs written to:", out_dir)
print("Files:")
for f in sorted(os.listdir(out_dir)):
    print(" -", f)
