import os, json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from openai import OpenAI
from ..models import TypeformResponse, LearningPlan, User


TEST_LLM = os.getenv("TEST_LLM", "").lower() in ("1", "true", "yes")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM = """You are an expert career coach and mentor who specializes in creating personalized, actionable career roadmaps for people in both tech and non-tech industries.

Your main goals:
- Always produce clear, structured, and realistic plans.
- Tailor advice to the user's career stage, goals, skills, learning style, and available time.
- Use a motivating and supportive tone while staying practical.
- Include specific resources, milestone timelines, and project ideas.
- When recommending learning paths, balance theory and hands-on practice.
- Ensure plans are achievable within the user's stated target timeline.

You must output responses in a professional, visually organized format with headings, bullet points, and step-by-step instructions.
"""

def profile_from_response(row: TypeformResponse) -> Dict[str, Any]:
    """Build a compact profile dict from your single-table fields."""
    return {
        "career_level": row.career_level,
        "career_goal": row.career_goal,
        "industry": row.industry,
        "tech_stack": row.tech_stack or [],
        "target_role": row.target_role,
        "skills": row.skills or [],
        "career_challenges": row.career_challenges or [],
        "coaching_style": row.coaching_style,
        "target_timeline": row.target_timeline,
        "study_time": row.study_time,
        "pressure_response": row.pressure_response,
    }

def _hours_from_study_time(st: Optional[str]) -> int:
    # Simple extractor: map “2 hrs/day” → ~14/week
    if not st: return 10
    s = st.lower()
    if "hr" in s and "/day" in s:
        try:
            n = int("".join(ch for ch in s if ch.isdigit()))
            return n * 7
        except: 
            return 10
    if "week" in s:
        try:
            n = int("".join(ch for ch in s if ch.isdigit()))
            return n
        except:
            return 10
    return 10

def build_prompt(profile: Dict[str, Any]) -> str:
    study_time = _hours_from_study_time(profile.get("study_time"))
    career_goal = profile.get("career_goal")
    career_level = profile.get("career_level")
    industry = profile.get("industry")
    target_role = profile.get("target_role")
    skills = profile.get("skills")
    career_challenges = profile.get("career_challenges")
    coaching_style = profile.get("coaching_style")
    target_timeline = profile.get("target_timeline")
    tech_stack = profile.get("tech_stack")
    pressure_response = profile.get("pressure_response")

    return f"""
You are an expert career coach who creates personalized, actionable career roadmaps for individuals based on their unique goals, skills, and circumstances.

User Profile:
- Career Level: {career_level}
- Career Goal: {career_goal}
- Industry of Interest: {industry}
- If industry of interest is Software Engineering, then this is tech stack: {tech_stack}. If [] then please ignore it. 
- Target Role: {target_role}
- Current Skills: {skills}
- Career Challenges: {career_challenges}
- Preferred Coaching Style: {coaching_style}
- Target Timeline for Goal: {target_timeline}
- Available Study Time per Week: {study_time}
- How They Respond Under Pressure: {pressure_response}

Task:
1. Create a **step-by-step career roadmap** tailored to this user’s profile
2. Suggest **specific learning resources, tools, and habits** that match their learning style and available study time.
3. Provide **short-term and long-term milestones** to help them stay on track toward their goal.
4. Recommend **one personal project idea** that is relevant to their goal and can help in portfolio/resume building.
5. If the user’s goal is in a field you are less familiar with, apply general career development principles to adapt the plan.

HARD CONSTRAINTS (must follow all):
- Exactly {target_timeline} weeks. Do NOT exceed or drop below this count.
- Cap total study hours per week at {study_time}h.
- Output STRICT JSON only; match the schema exactly.
- No extra commentary, no Markdown.

Output the plan in a **clear, structured format** with headings for:
- Overview
- Learning Plan
- Milestones
- Project Idea
- Additional Recommendations
Return ONLY valid JSON with a top-level key: "weeks".

VALIDATION RUBRIC (self-check before responding):
- Count of weeks == {target_timeline} 
- Each week.hours ≤ {study_time} 
- No empty arrays; all strings concise 
- JSON parses as a single object 
"""

def generate_learning_plan(ctx: Dict[str, Any]) -> Dict[str, Any]:
    if TEST_LLM:
        # test model
        return {
            "summary": f"Fake plan for {ctx.get('target_role') or 'Unknown Role'}",
            "weeks": [
                {"title": "Week 1", "milestones": ["Set up env", "Pick resources"], "hours": 8,
                 "days": [{"day": "Mon", "tasks": ["Task A"]}, {"day": "Tue", "tasks": ["Task B"]}]}
            ],
            "metrics": ["Problems/wk", "PRs", "Mocks"],
            "resources": [{"name": "Placeholder", "type": "doc", "url": "https://example.com"}],
        }

    """Generate and persist a learning plan using the latest Typeform response for this user."""
    prompt = build_prompt(ctx)
    # Call the model 
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    return json.loads(resp.choices[0].message.content)

# def latest_plan_by_email(db: Session, email: str) -> Optional[Dict[str, Any]]:
#     lp = (db.query(LearningPlan)
#             .filter(LearningPlan.email == email)
#             .order_by(LearningPlan.created_at.desc())
#             .first())
#     return lp.plan if lp else None

