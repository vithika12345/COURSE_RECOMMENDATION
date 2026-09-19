import json
import os
import re
from typing import Any, Dict, List

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from groq import Groq
from tavily import TavilyClient

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder="static")
CORS(app)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None


def clean_json_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text


def safe_int(value, default=8):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def normalize_plan(data: Dict[str, Any], profile: Dict[str, Any], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    data = data if isinstance(data, dict) else {}
    recs = data.get("recommendations") or []
    weeks = data.get("roadmap") or []

    normalized_recs = []
    for i, item in enumerate(recs[:8]):
        if not isinstance(item, dict):
            continue
        normalized_recs.append({
            "title": str(item.get("title") or f"Recommended Resource {i+1}"),
            "platform": str(item.get("platform") or "Web"),
            "url": str(item.get("url") or ""),
            "level": str(item.get("level") or profile.get("level", "Beginner")),
            "reason": str(item.get("reason") or "Matches the learner's stated goal."),
            "skills": item.get("skills") if isinstance(item.get("skills"), list) else [],
            "estimated_hours": safe_int(item.get("estimated_hours"), 4),
        })

    normalized_weeks = []
    for i, item in enumerate(weeks[:16]):
        if not isinstance(item, dict):
            continue
        normalized_weeks.append({
            "week": safe_int(item.get("week"), i + 1),
            "focus": str(item.get("focus") or "Core learning"),
            "objectives": item.get("objectives") if isinstance(item.get("objectives"), list) else [],
            "tasks": item.get("tasks") if isinstance(item.get("tasks"), list) else [],
            "deliverable": str(item.get("deliverable") or "Complete the week's practice."),
            "hours": safe_int(item.get("hours"), 5),
        })

    return {
        "summary": str(data.get("summary") or f"A personalized path for {profile.get('goal', 'your learning goal')}."),
        "strategy": str(data.get("strategy") or "Build foundations, practice, then complete a project."),
        "recommendations": normalized_recs,
        "roadmap": normalized_weeks,
        "milestones": data.get("milestones") if isinstance(data.get("milestones"), list) else [],
        "sources": sources,
        "profile": profile,
    }


def fallback_plan(profile: Dict[str, Any], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    goal = profile.get("goal", "your target skill")
    hours = safe_int(profile.get("weekly_hours"), 8)
    weeks = safe_int(profile.get("duration_weeks"), 8)
    interests = [x.strip() for x in str(profile.get("interests", "")).split(",") if x.strip()]

    generic = [
        ("Foundations", "Understand the core concepts and terminology."),
        ("Guided Practice", "Follow a structured course and reproduce small examples."),
        ("Hands-on Practice", "Solve exercises and build small components."),
        ("Applied Project", "Build a portfolio-sized project connected to your goal."),
        ("Review & Portfolio", "Refactor, document and present your work."),
    ]

    roadmap = []
    for i in range(min(weeks, 12)):
        focus, objective = generic[min(i, len(generic) - 1)]
        roadmap.append({
            "week": i + 1,
            "focus": focus,
            "objectives": [objective, f"Practice for about {hours} hours this week."],
            "tasks": ["Study the topic", "Take notes", "Complete hands-on exercises"],
            "deliverable": "A small working artifact or set of solved exercises.",
            "hours": hours,
        })

    return normalize_plan({
        "summary": f"Start with foundations for {goal}, then move from guided practice to an applied project.",
        "strategy": "Learn → practice → build → review.",
        "recommendations": [{
            "title": f"Search-backed resources for {goal}",
            "platform": "Tavily Web Research",
            "url": sources[0]["url"] if sources else "",
            "level": profile.get("level", "Beginner"),
            "reason": "Selected from the current web research context.",
            "skills": interests,
            "estimated_hours": 5
        }] if sources else [],
        "roadmap": roadmap,
        "milestones": ["Understand foundations", "Complete guided practice", "Build a project", "Publish/document the result"]
    }, profile, sources)


def search_web(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not tavily_client:
        return []
    query = (
        f"best courses tutorials learning resources for {profile.get('goal')} "
        f"{profile.get('interests', '')} level {profile.get('level')} "
        f"learner portfolio project"
    )
    result = tavily_client.search(
        query=query,
        search_depth="basic",
        topic="general",
        max_results=8,
        include_answer=False
    )
    sources = []
    for item in result.get("results", []):
        sources.append({
            "title": item.get("title", "Untitled resource"),
            "url": item.get("url", ""),
            "snippet": item.get("content", "")[:500],
            "score": round(float(item.get("score", 0) or 0), 3),
        })
    return sources


def generate_with_groq(profile: Dict[str, Any], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not groq_client:
        return fallback_plan(profile, sources)

    source_text = "\n".join(
        f"- {s['title']} | {s['url']} | {s['snippet']}"
        for s in sources
    )[:10000]

    schema = {
        "summary": "short personalized summary",
        "strategy": "short learning strategy",
        "recommendations": [
            {
                "title": "resource/course title",
                "platform": "platform",
                "url": "URL from supplied sources only when possible",
                "level": "Beginner/Intermediate/Advanced",
                "reason": "specific reason",
                "skills": ["skill1", "skill2"],
                "estimated_hours": 5
            }
        ],
        "roadmap": [
            {
                "week": 1,
                "focus": "topic",
                "objectives": ["objective"],
                "tasks": ["task"],
                "deliverable": "small output",
                "hours": 6
            }
        ],
        "milestones": ["milestone 1", "milestone 2"]
    }

    prompt = f"""
You are the Recommendation Agent inside an Agentic AI learning-path orchestrator.
Create a practical, realistic learning plan. Do not invent URLs. Prefer the supplied Tavily URLs.
Return ONLY valid JSON matching this schema:
{json.dumps(schema)}

Learner profile:
{json.dumps(profile, indent=2)}

Current web research:
{source_text or "No web sources were returned. Use general knowledge but do not fabricate URLs."}

Rules:
- Match the learner's level and weekly time.
- Keep the path achievable within the requested duration.
- Include prerequisites before advanced topics.
- Recommend 3-6 resources.
- Give concrete weekly tasks and a deliverable.
- Make recommendations explainable.
- If sources are supplied, use their exact URLs.
"""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0.25,
        messages=[
            {"role": "system", "content": "You output strict JSON and act as a learning-path planning agent."},
            {"role": "user", "content": prompt},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    return json.loads(clean_json_text(raw))


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)


@app.get("/api/health")
def health():
    return jsonify({
        "ok": True,
        "groq_configured": bool(GROQ_API_KEY),
        "tavily_configured": bool(TAVILY_API_KEY),
        "model": GROQ_MODEL,
    })


@app.post("/api/search")
def api_search():
    try:
        profile = request.get_json(force=True) or {}
        if not TAVILY_API_KEY:
            return jsonify({"ok": False, "error": "TAVILY_API_KEY is not configured in .env"}), 400
        return jsonify({"ok": True, "sources": search_web(profile)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/api/generate")
def api_generate():
    try:
        profile = request.get_json(force=True) or {}
        if not profile.get("goal"):
            return jsonify({"ok": False, "error": "Please enter a learning goal."}), 400

        sources = search_web(profile) if tavily_client else []
        plan_data = generate_with_groq(profile, sources)
        plan = normalize_plan(plan_data, profile, sources)

        return jsonify({
            "ok": True,
            "plan": plan,
            "agents": [
                {"name": "Profile Agent", "status": "complete", "detail": "Learner profile structured"},
                {"name": "Research Agent", "status": "complete", "detail": f"{len(sources)} web sources gathered"},
                {"name": "Recommendation Agent", "status": "complete", "detail": "Courses matched to goal and level"},
                {"name": "Roadmap Agent", "status": "complete", "detail": f"{len(plan['roadmap'])} learning weeks planned"},
            ]
        })
    except json.JSONDecodeError:
        return jsonify({"ok": False, "error": "Groq returned invalid JSON. Please try again."}), 502
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
