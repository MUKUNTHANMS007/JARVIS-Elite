/**
 * J.A.R.V.I.S. Neural Protocol v1.0
 * Unified schema for real-time synchronization between the Cognitive Layer (Python)
 * and the Interaction Layer (React/Three.js).
 */

export type AgentState = "IDLE" | "THINKING" | "SPEAKING" | "LISTENING" | "TOOL_EXECUTING";

export interface Telemetry {
  cpu_percent: number;
  ram_percent: number;
  mood_score: number; // 0.0 (Calm/Emerald) to 1.0 (Stressed/Crimson)
  is_online: boolean;
}

export interface DashboardMetrics {
  unread_mail: number;
  spotify_track: string;
  reminder_count: number;
  leetcode_status: any;
  github_pulse: any;
}

export interface ProactiveAlert {
  id: string;
  type: "MEETING_ALERT" | "SECURITY_SENTINEL" | "HEALTH_RECOV" | "SYSTEM_CRITICAL";
  title: string;
  message: string;
  timestamp: number;
  priority: "LOW" | "NORMAL" | "HIGH" | "CRITICAL";
}

export interface NeuralPacket {
  type: "NEURAL_PULSE" | "AGENT_STATE_CHANGE" | "PROACTIVE_ALERT";
  timestamp: number;
  
  // Cognitive State
  state: AgentState;
  
  // Real-time metrics
  telemetry: Telemetry;
  
  // Display data
  dashboard?: DashboardMetrics;
  
  // Optional payloads
  active_tool?: string;
  alert?: ProactiveAlert;
}
