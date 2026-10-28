export type AssistantState =
  | 'idle'
  | 'listening'
  | 'processing'
  | 'executing'
  | 'speaking'
  | 'error'
  | 'waiting_confirmation';

export interface CommandExecutionResult {
  success: boolean;
  intent: string;
  status: string;
  response_text: string;
  entities: Record<string, any>;
  risk_level: 'low' | 'medium' | 'high';
  requires_confirmation: boolean;
  confirmation_id?: string;
  execution_time_ms: number;
  history_id?: number;
  data?: Record<string, any>;
}

export interface ConversationTurn {
  id: string;
  timestamp: string;
  user_text: string;
  response_text: string;
  intent: string;
  status: string;
  risk_level: string;
}

export interface SystemStatus {
  cpu_percent: number;
  cpu_count: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_free_gb: number;
  disk_total_gb: number;
  battery_percent?: number | null;
  is_charging?: boolean | null;
  os_name: string;
  os_version: string;
  hostname: string;
  uptime_seconds: number;
  is_online: boolean;
}

export interface ReminderItem {
  id: number;
  title: string;
  due_time: string;
  is_completed: boolean;
  is_recurring: boolean;
  recurrence_pattern?: string | null;
  created_at?: string;
}

export interface AppRegistryItem {
  id: number;
  app_key: string;
  display_name: string;
  aliases: string[];
  exec_path: string;
  is_custom: boolean;
  is_available: boolean;
}

export interface HistoryItem {
  id: number;
  command_text: string;
  recognized_intent: string;
  entities: Record<string, any>;
  status: string;
  risk_level: string;
  response_text?: string;
  execution_time_ms: number;
  created_at: string;
}

export interface AnalyticsData {
  total_commands: number;
  successful_commands: number;
  failed_commands: number;
  success_rate_percent: number;
  average_response_time_ms: number;
  commands_today: number;
  most_used_intents: { intent: string; count: number }[];
  most_used_apps: { app: string; count: number }[];
  commands_timeline: { date: string; count: number }[];
}

export interface AppSettings {
  app_name: string;
  wake_word: string;
  wake_word_enabled: boolean;
  default_language: string;
  tts_rate: number;
  tts_volume: number;
  tts_voice_id?: string | null;
  clipboard_permission_enabled: boolean;
  require_confirmation_high_risk: boolean;
  require_confirmation_med_risk: boolean;
  demo_mode: boolean;
  default_browser: string;
  default_music_app: string;
  theme: string;
  has_openai_key: boolean;
  openai_api_key?: string;
}

export interface HelpCategory {
  category: string;
  icon: string;
  commands: { text: string; description: string }[];
}

export interface DemoSample {
  command: string;
  intent: string;
  description: string;
}
