from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from services.evolution_service import get_or_generate_evolution_challenge, verify_evolution_solution, get_evolution_heatmap
from voice.tts import synthesize_speech
import json

router = APIRouter()

@router.get("/today")
async def get_today_challenge(lang: str = "python"):
    challenge = await get_or_generate_evolution_challenge(lang)
    if not challenge:
        # Fallback problem if no leetcode scheduled
        return {
            "title": "Reverse Linked List",
            "difficulty": "Easy",
            "description": "Reverse a singly linked list in-place.",
            "broken_code": "def reverseList(head):\n    prev = None\n    curr = head\n    while curr:\n        next_node = curr.next\n        curr.next = prev\n        prev = curr\n    return head # FIXME: Logic drift",
            "hint": "Ensure 'curr' advances properly to avoid an infinite loop.",
            "language": lang,
            "streak": 5
        }
    
    heatmap = await get_evolution_heatmap()
    return {**challenge, "heatmap": heatmap}

@router.get("/heatmap")
async def get_pulse_heatmap():
    heatmap = await get_evolution_heatmap()
    return heatmap

@router.post("/submit")
async def submit_challenge(request: Request):
    try:
        body = await request.json()
        code = body.get("code")
        lang = body.get("language", "python")
        problem_id = body.get("id")
        
        result = await verify_evolution_solution(problem_id, code, lang)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/hint")
async def speak_hint(request: Request):
    """
    JARVIS speaks the hint and returns the text.
    """
    try:
        body = await request.json()
        hint_text = body.get("hint", "Sir, consider the edge cases of the algorithm.")
        
        # Synthesize audio for the hint
        # audio_content = await synthesize_speech(f"Sir, {hint_text}")
        # In a real environment, we'd stream this or return the URL.
        # For now, we confirm the hint and trigger TTS on the frontend context if possible.
        
        return {"status": "success", "hint": hint_text}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
