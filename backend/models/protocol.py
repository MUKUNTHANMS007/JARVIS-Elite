from pydantic import BaseModel, Field
from typing import Optional, List, Any, Literal
from datetime import datetime

class AgentState(BaseModel):
    state: Literal["IDLE", "THINKING", "SPEAKING", "LISTENING", "TOOL_EXECUTING"] = "IDLE"

class Telemetry(BaseModel):
    cpu_percent: float
    ram_percent: float
    mood_score: float = 0.0  # 0.0 to 1.0
    is_online: bool = True

class DashboardMetrics(BaseModel):
    unread_mail: int = 0
    spotify_track: str = "Standby"
    reminder_count: int = 0
    leetcode_status: Optional[Any] = None
    github_pulse: Optional[Any] = None

class ProactiveAlert(BaseModel):
    id: str
    type: Literal["MEETING_ALERT", "SECURITY_SENTINEL", "HEALTH_RECOV", "SYSTEM_CRITICAL"]
    title: str
    message: str
    timestamp: float
    priority: Literal["LOW", "NORMAL", "HIGH", "CRITICAL"] = "NORMAL"

class NeuralPacket(BaseModel):
    type: Literal["NEURAL_PULSE", "AGENT_STATE_CHANGE", "PROACTIVE_ALERT"]
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    state: Literal["IDLE", "THINKING", "SPEAKING", "LISTENING", "TOOL_EXECUTING"] = "IDLE"
    telemetry: Telemetry
    dashboard: Optional[DashboardMetrics] = None
    active_tool: Optional[str] = None
    alert: Optional[ProactiveAlert] = None
