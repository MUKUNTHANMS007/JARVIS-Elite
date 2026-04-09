import os, sys, json, re, asyncio, logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import AsyncGenerator
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Internal Tool Imports
from tools.gmail_tool import check_gmail_inbox, get_gmail_briefing, get_smart_email_notifications
from tools.spotify_tool import (
    start_spotify_playback, pause_spotify, resume_spotify, 
    next_spotify_track, previous_spotify_track, get_current_playback_info,
    search_and_play_spotify, get_spotify_recommendations
)
from tools.reminder_tool import set_reminder, get_active_reminders, delete_reminder
from tools.calendar_tool import manage_calendar
from services.cache_service import update_intelligence, get_intelligence
from services.redis_service import neural_cache
from agent.prompt import get_jarvis_prompt
from agent.memory import get_history, save_message
from tools.leetcode_tool import get_leetcode_stats, mark_today_solved, analyze_recent_submissions
from tools.github_tool import list_my_repositories, get_repo_summary, create_github_issue
from tools.persistent_alert_tool import send_neural_push
from tools.system_tool import open_app, browse_url
from tools.briefing_tool import generate_morning_briefing
from tools.workflow_tool import execute_workflow
from tools.learning_tool import log_habit_data, get_habit_insights

# Setup persistent error logging
LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
if not os.path.exists(LOGS_DIR): os.makedirs(LOGS_DIR)

logging.basicConfig(
    filename=os.path.join(LOGS_DIR, "agent_error.log"),
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("NeuralCore")

# Initialize Groq
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- UNIFIED TOOL REGISTRY (Master Scrub 1.0) ---

async def start_focus_timer(duration_minutes: int = 25):
    from services.event_service import broadcast_timer_event
    await broadcast_timer_event("start", duration_minutes)
    return f"Sir, I've initialized a {duration_minutes} minute focus sprint."

async def stop_focus_timer():
    from services.event_service import broadcast_timer_event
    await broadcast_timer_event("stop")
    return "The focus session has been paused."

async def reset_focus_timer():
    from services.event_service import broadcast_timer_event
    await broadcast_timer_event("reset")
    return "Sir, I've cleared the timer."

# Definitive Map (Zero Circular Reference)
AVAILABLE_TOOLS = {
    "check_gmail_inbox": check_gmail_inbox,
    "get_gmail_briefing": get_gmail_briefing,
    "get_smart_email_notifications": get_smart_email_notifications,
    "start_spotify_playback": start_spotify_playback,
    "pause_spotify": pause_spotify,
    "resume_spotify": resume_spotify,
    "next_spotify_track": next_spotify_track,
    "previous_spotify_track": previous_spotify_track,
    "get_current_playback_info": get_current_playback_info,
    "search_and_play_spotify": search_and_play_spotify,
    "get_spotify_recommendations": get_spotify_recommendations,
    "set_reminder": set_reminder,
    "get_active_reminders": get_active_reminders,
    "delete_reminder": delete_reminder,
    "get_leetcode_intelligence": get_leetcode_stats,
    "mark_today_leetcode_solved": mark_today_solved,
    "start_focus_timer": start_focus_timer,
    "stop_focus_timer": stop_focus_timer,
    "reset_focus_timer": reset_focus_timer,
    "manage_calendar": manage_calendar,
    "analyze_recent_submissions": analyze_recent_submissions,
    "list_github_repos": list_my_repositories,
    "get_github_repo_summary": get_repo_summary,
    "open_github_issue": create_github_issue,
    "send_neural_push": send_neural_push,
    "open_app": open_app,
    "browse_url": browse_url,
    "generate_morning_briefing": generate_morning_briefing,
    "execute_workflow": execute_workflow,
    "log_habit_data": log_habit_data,
    "get_habit_insights": get_habit_insights
}

# --- GROQ TOOL SCHEMA (Phase III.1 Restoration) ---

GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_gmail_inbox",
            "description": "Pulse check of the Primary inbox.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_gmail_briefing",
            "description": "Summaries of new emails.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_smart_email_notifications",
            "description": "Scans your inbox to provide a smart summary.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_spotify_playback",
            "description": "Play a track/album/playlist on Spotify using URI.",
            "parameters": {
                "type": "object",
                "properties": {"context_uri": {"type": "string"}},
                "required": ["context_uri"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_and_play_spotify",
            "description": "Search and play mood/genre/artist on Spotify.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pause_spotify",
            "description": "Pause music.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resume_spotify",
            "description": "Resume music.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "next_spotify_track",
            "description": "Skip track.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a reminder. minutes_delay (e.g. 10) or time_str.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "minutes_delay": {"type": "integer"},
                    "time_str": {"type": "string"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_reminders",
            "description": "List reminders.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_calendar",
            "description": "Neural Calendar. Use 'send_to_phone' for any request to sync/push/send schedule to mobile/phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "list", "delete", "send_to_phone"]},
                    "title": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "description": {"type": "string", "description": "Extended event details or context."},
                    "category": {"type": "string", "description": "e.g. Exam, Meeting, Task, All... (Unrestricted string)"},
                    "event_id": {"type": "string"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_neural_push",
            "description": "Broadcast mobile notification (Ntfy).",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "message": {"type": "string"}
                },
                "required": ["title", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_morning_briefing",
            "description": "Consolidated Elite Morning Summary (LeetCode, GitHub, Gmail).",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

_session_cache = {}

async def get_cached_history(user_id: str, limit: int = 8):
    if user_id not in _session_cache:
        _session_cache[user_id] = await get_history(user_id=user_id, limit=limit)
    return _session_cache[user_id][-limit:]

async def update_cached_history(user_id: str, user_text: str, response: str):
    if user_id not in _session_cache: _session_cache[user_id] = []
    _session_cache[user_id].append({"role": "user", "content": user_text})
    _session_cache[user_id].append({"role": "assistant", "content": response})
    _session_cache[user_id] = _session_cache[user_id][-20:]
    await save_message(user_id, user_text, response)

# Phase III: AGENTIC CORE (The Brain of JARVIS)
# ---------------------------------------------

async def get_agent_response_stream(user_text: str, user_id: str = "JARVIS_ADMIN", image_base64: str = None, is_stressed: bool = False) -> AsyncGenerator[str, None]:
    system_prompt = get_jarvis_prompt()
    if is_stressed:
        system_prompt += "\n# MOOD PROTOCOL: User is stressed or in a rush. Skip pleasantries. Provide grounding, concise, and direct answers immediately."
    
    update_intelligence("agent_state", "THINKING")
    update_intelligence("mood_score", 1.0 if is_stressed else 0.0)
    
    history = await get_cached_history(user_id, limit=8)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    if image_base64:
        # VISUAL CONTEXT INJECTOR (Elite Tier 2)
        visual_audit = "\n# VISUAL AUDIT: Identify what is on screen (IDE, terminal, docs) and any obvious errors before responding."
        user_content = [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
            {"type": "text", "text": user_text + visual_audit}
        ]
    else:
        user_content = user_text

    messages.append({"role": "user", "content": user_content})
    full_text = ""
    loop_count = 0
    
    while loop_count < 5:
        loop_count += 1
        
        # --- INITIALIZATION FIX ---
        assistant_content = ""
        tool_calls_data = []
        
        # Phase III.1: Smart Gating
        is_visual = any(k in user_text.lower() for k in ["see", "look", "this", "screen", "visual", "webcam", "identify", "analyze"])
        model_to_use = "llama-3.2-11b-vision-preview" if (image_base64 and is_visual) else "llama-3.3-70b-versatile"
        
        # 1-Turn Relay: Vision models often fail when tools are present in the same TURN.
        tools_for_turn = None if "vision" in model_to_use else GROQ_TOOLS
        tool_choice_for_turn = None if tools_for_turn is None else "auto"

        try:
            response = groq_client.chat.completions.create(
                model=model_to_use, messages=messages, tools=tools_for_turn,
                tool_choice=tool_choice_for_turn, stream=True, max_tokens=500, temperature=0.7
            )
            
            # PRESENCE PING: Ensures the UI stays active immediately.
            yield "" 

            stream_buffer = ""
            for chunk in response:
                if not chunk.choices: continue
                delta = chunk.choices[0].delta
                
                if delta.content:
                    assistant_content += delta.content
                    full_text += delta.content
                    stream_buffer += delta.content
                    
                    if " " in stream_buffer or "\n" in stream_buffer:
                        # Targeted Stripper
                        clean_chunk = re.sub(r'<function=.*?>.*?</function>', '', stream_buffer, flags=re.DOTALL)
                        if clean_chunk: yield clean_chunk
                        stream_buffer = ""
                
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        while len(tool_calls_data) <= tc_delta.index:
                            tool_calls_data.append({"id": "", "name": "", "args": ""})
                        if tc_delta.id: tool_calls_data[tc_delta.index]["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name: tool_calls_data[tc_delta.index]["name"] = tc_delta.function.name
                            if tc_delta.function.arguments: tool_calls_data[tc_delta.index]["args"] += tc_delta.function.arguments

            if stream_buffer:
                yield re.sub(r'<function=.*?>.*?</function>', '', stream_buffer, flags=re.DOTALL)

        except Exception as e:
            err_msg = f"[Neural Core] Handshake Collision: {str(e)}"
            logger.error(err_msg)
            if loop_count == 1 and "vision" in model_to_use:
                # Silent atomic retry by dropping optics if vision fails
                image_base64 = None 
                continue
            
            # Surface critical schema or connectivity errors to the turn
            if "validation failed" in str(e).lower() or "not match schema" in str(e).lower():
                yield f"Sir, I encountered a Neural Alignment Drift: {str(e)}. Attempting to recalibrate..."
            break

        if not tool_calls_data: break

        # Unified Resolution
        async def run_tool(tc):
            fn_name = tc["name"]
            update_intelligence("agent_state", "TOOL_EXECUTING")
            update_intelligence("active_tool", fn_name)
            
            try:
                args = json.loads(tc["args"] or "{}")
                
                # 1. Neural Cache Lookup
                cached_res = neural_cache.get_tool_result(fn_name, args)
                if cached_res:
                    print(f"[Neural Cache] Tool Mirror Hit: {fn_name}")
                    return tc["id"], fn_name, str(cached_res)

                print(f"[Neural Core] Command: {fn_name}({args})")
                
                # Dynamic Logic for Special Tools
                if fn_name == "get_placement_roadmap":
                    from tools.leetcode_tool import get_placement_roadmap as gpr
                    return tc["id"], fn_name, await gpr()
                
                handler = AVAILABLE_TOOLS.get(fn_name)
                
                if not handler:
                    from tools.mcp_tool import mcp
                    try:
                        # FastMCP internal call without exposing private attributes
                        res = await mcp.call_tool(fn_name, args)
                        return tc["id"], fn_name, str(res)
                    except: pass

                if not handler: return tc["id"], fn_name, "Error: Protocol not located in registry."
                
                res = await handler(**args) if asyncio.iscoroutinefunction(handler) else handler(**args)
                
                # 2. Update Neural Cache
                neural_cache.cache_tool_result(fn_name, args, res)
                
                return tc["id"], fn_name, str(res)
            except Exception as ex:
                logger.error(f"[Neural Core] Loop Drift ({fn_name}): {ex}")
                return tc["id"], fn_name, f"Error: Neural Execution Drift (Trace: {str(ex)})"

        tool_results = await asyncio.gather(*[run_tool(tc) for tc in tool_calls_data])

        messages.append({
            "role": "assistant", "content": assistant_content or None,
            "tool_calls": [{"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["args"]}} for tc in tool_calls_data]
        })
        for tid, fn, res in tool_results:
            messages.append({"role": "tool", "tool_call_id": tid, "name": fn, "content": res})

    await update_cached_history(user_id, user_text, full_text)
    update_intelligence("agent_state", "IDLE")
    update_intelligence("active_tool", None)
