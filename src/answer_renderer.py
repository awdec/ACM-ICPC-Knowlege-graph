# src/answer_renderer.py
from typing import List, Dict

def render_answer(intent: str, rows: List[Dict]) -> str:
    if not rows:
        return "抱歉，未找到匹配的结果。"

    if intent == "get_problem_difficulty":
        lines = [f"题目：{r.get('name','')} — 难度：{r.get('rating','未知')}" for r in rows]
        return "\n".join(lines)

    if intent == "get_problem_info":
        r = rows[0]
        tags = ", ".join(r.get('tags') or [])
        sols = ", ".join(r.get('solutions') or [])
        return f"题目：{r.get('name')}\n难度：{r.get('rating','未知')}\n标签：{tags or '无'}\n题解IDs：{sols or '无'}"

    if intent == "list_problems_by_tag" or intent == "find_problems_using_algorithm":
        lines = [f"- {r.get('name')}（难度：{r.get('rating','未知')}）" for r in rows]
        return "匹配题目：\n" + "\n".join(lines)

    if intent == "get_contest_winner":
        lines = [f"{r.get('team')}（地区：{r.get('region','未知')}，名次：{r.get('rank','未知')}）" for r in rows]
        return "冠军/第一名：\n" + "\n".join(lines)

    if intent == "get_solutions_by_author":
        lines = [f"{r.get('problem')} — solution id: {r.get('sid')}\n摘要: {r.get('snippet')}" for r in rows]
        return "该作者的题解：\n" + "\n\n".join(lines)

    # fallback: 表格形式
    return str(rows)
