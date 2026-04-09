import os
import json
import asyncio
from datetime import date, datetime, timedelta, timezone
from agent.memory import supabase, init_db
from agent.core import groq_client
from services.scheduler_service import get_today_scheduled_problem

async def get_supabase():
    global supabase
    if not supabase:
        await init_db()
    from agent.memory import supabase as sb
    return sb

async def get_or_generate_evolution_challenge(language: str = "python"):
    """
    JARVIS Evolution Engine:
    1. Fetches today's problem from the scheduler.
    2. If no broken code exists in memory, use Groq to 'break' the solution.
    3. Returns the high-fidelity challenge object.
    """
    problem = await get_today_scheduled_problem()
    if not problem:
        return None

    # For dynamic generation, we ask the LLM to 'break' the logic
    # In a production J.A.R.V.I.S., we would cache this in Supabase.
    # For now, we generate it on-the-fly for the highest variety.
    
    language_constraints = {
        "python": "Use Python syntax: 'def function_name(args):', 4-space indentation, no semicolons.",
        "java": "Use Java syntax: 'public class Solution { public ... }', semicolons, camelCase, explicit types."
    }

    prompt = f"""
    You are JARVIS, an elite coding coach. 
    Problem: {problem['title']}
    Difficulty: {problem['difficulty']}
    Description: {problem['slug']}
    Target Language: {language}

    STRICT_LANGUAGE_ENFORCEMENT:
    - {language_constraints.get(language, language_constraints['python'])}
    - DO NOT use syntax from other languages.
    - {f"If Java: Start with 'public class Solution {{ ... }}'" if language == "java" else ""}

    TASK:
    1. Generate a professional problem description.
    2. Provide a 'Broken' (Python) or 'Skeleton/Broken' (Java) version.
       - {f"Java code must be a complete class structure with a logical bug in the method body." if language == "java" else "Python code must have a subtle logic bug."}
    3. Provide a 'Correct' solution for internal verification.
    4. Provide a tactical 1-sentence hint.
    5. Provide 3 sample test cases.

    Return ONLY a JSON object:
    {{
        "description": "...",
        "broken_code": "...",
        "correct_code": "...",
        "hint": "...",
        "test_cases": [
            {{"input": "...", "expected": "...", "status": "pending"}},
            {{"input": "...", "expected": "...", "status": "pending"}},
            {{"input": "...", "expected": "...", "status": "pending"}}
        ],
        "language": "{language}"
    }}
    """

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        challenge_data = json.loads(response.choices[0].message.content)
        
        return {
            **problem,
            **challenge_data
        }
    except Exception as e:
        print(f"[Evolution Service] Generation failed: {e}")
        return None

async def verify_evolution_solution(problem_id: str, user_code: str, language: str, is_dry_run: bool = False):
    """
    Uses LLM to verify if the user's fixed code is logically equivalent to the solution.
    """
    prompt = f"""
    Verify this fixed code for the problem.
    User Code ({language}):
    {user_code}

    Does this code correctly solve the logic and handle edge cases? 
    Return ONLY a JSON object:
    {{
        "valid": true/false,
        "feedback": "1-sentence feedback from JARVIS.",
        "xp_gain": 12
    }}
    """
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant", # Faster for validation
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        
        # PERSISTENCE: Record success in Supabase ONLY IF NOT A DRY RUN
        if result.get("valid") and not is_dry_run:
            sb = await get_supabase()
            if sb:
                # 1. Update overall skill mastery
                res = await sb.table("skill_mastery").select("problems_solved").eq("user_id", "JARVIS_ADMIN").eq("category", "Neural Logic").limit(1).execute()
                current = res.data[0].get("problems_solved", 0) if res.data else 0
                
                await sb.table("skill_mastery").upsert({
                    "user_id": "JARVIS_ADMIN",
                    "category": "Neural Logic",
                    "problems_solved": current + 1,
                    "last_practiced": datetime.utcnow().isoformat()
                }, on_conflict="user_id, category").execute()

                # 2. Add log entry for Heat Map
                await sb.table("evolution_history").insert({
                    "user_id": "JARVIS_ADMIN",
                    "problem_title": problem_id,
                    "language": language,
                    "xp_gained": result.get("xp_gain", 12)
                }).execute()

        return result
    except Exception as e:
        print(f"[Evolution Service] Verification failed: {e}")
        return {"valid": False, "feedback": "Sir, I encountered a drift in my verification logic."}

async def get_evolution_heatmap(user_id: str = "JARVIS_ADMIN"):
    """
    Returns completion data for the last 30 days for the heat map.
    """
    try:
        sb = await get_supabase()
        if not sb: return []
        
        # Fetch from the pulse view we created in SQL
        result = await sb.table("evolution_history") \
            .select("completed_at") \
            .eq("user_id", user_id) \
            .gte("completed_at", (datetime.utcnow() - timedelta(days=30)).isoformat()) \
            .execute()
        
        # Aggregate by day for the frontend
        history = result.data
        daily_counts = {}
        for entry in history:
            # Use the first 10 chars (YYYY-MM-DD) to handle both 'T' and space separators
            day = entry['completed_at'][:10]
            daily_counts[day] = daily_counts.get(day, 0) + 1
            
        return daily_counts
    except Exception as e:
        print(f"[Evolution Service] Heatmap fetch failed: {e}")
        return {}
