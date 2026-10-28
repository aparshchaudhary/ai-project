import {
  CommandExecutionResult,
  SystemStatus,
  ReminderItem,
  AppRegistryItem,
  HistoryItem,
  AnalyticsData,
  AppSettings,
  HelpCategory,
  DemoSample,
  AudioDeviceItem,
  AudioLevelResult,
  LatencyMetrics,
  SecurityPermissionsData,
  AuditLogEntry,
  DiagnosticsResult,
} from '../types';

const BASE_URL = window.location.port === '5173' ? 'http://127.0.0.1:8000' : '';


export const api = {
  // Commands
  async processCommand(text: string, options?: { session_id?: string; demo_mode?: boolean; confirmed?: boolean; confirmation_id?: string }): Promise<CommandExecutionResult> {
    const res = await fetch(`${BASE_URL}/api/command/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        session_id: options?.session_id || 'default',
        demo_mode: options?.demo_mode || false,
        confirmed: options?.confirmed,
        confirmation_id: options?.confirmation_id,
      }),
    });
    if (!res.ok) throw new Error('Failed to process command');
    return res.json();
  },

  async confirmCommand(confirmation_id: string, approved: boolean): Promise<CommandExecutionResult> {
    const res = await fetch(`${BASE_URL}/api/command/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmation_id, approved }),
    });
    if (!res.ok) throw new Error('Failed to confirm command');
    return res.json();
  },

  // Voice & Audio
  async listenDesktopMic(options?: {
    duration?: number;
    use_vad?: boolean;
    device_id?: number;
    auto_execute?: boolean;
  }): Promise<{
    success: boolean;
    text: string;
    error?: string;
    metrics?: LatencyMetrics;
    execution?: CommandExecutionResult;
  }> {
    const duration = options?.duration ?? 4.0;
    const useVad = options?.use_vad ?? true;
    const autoExec = options?.auto_execute ?? true;
    const devParam = options?.device_id !== undefined ? `&device_id=${options.device_id}` : '';
    const res = await fetch(`${BASE_URL}/api/voice/listen-desktop?duration=${duration}&use_vad=${useVad}&auto_execute=${autoExec}${devParam}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Desktop mic recording failed');
    return res.json();
  },

  async stopVoice(): Promise<void> {
    await fetch(`${BASE_URL}/api/voice/stop`, { method: 'POST' });
  },

  async getAudioDevices(): Promise<{ devices: AudioDeviceItem[]; selected_device_id: number | null }> {
    const res = await fetch(`${BASE_URL}/api/audio/devices`);
    if (!res.ok) throw new Error('Failed to fetch audio devices');
    return res.json();
  },

  async selectAudioDevice(deviceId: number): Promise<{ success: boolean; selected_device_id: number }> {
    const res = await fetch(`${BASE_URL}/api/audio/select-device`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_id: deviceId }),
    });
    if (!res.ok) throw new Error('Failed to select audio device');
    return res.json();
  },

  async testAudioLevel(deviceId?: number): Promise<AudioLevelResult> {
    const devParam = deviceId !== undefined ? `?device_id=${deviceId}` : '';
    const res = await fetch(`${BASE_URL}/api/audio/test-level${devParam}`);
    if (!res.ok) throw new Error('Audio level test failed');
    return res.json();
  },

  async transcribeAudioBlob(blob: Blob, filename = 'speech.wav'): Promise<{ success: boolean; text: string; error?: string }> {
    const formData = new FormData();
    formData.append('file', blob, filename);
    const res = await fetch(`${BASE_URL}/api/voice/transcribe`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Transcription failed');
    return res.json();
  },

  async speakText(text: string): Promise<void> {
    await fetch(`${BASE_URL}/api/voice/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
  },

  // System
  async getSystemStatus(): Promise<SystemStatus> {
    const res = await fetch(`${BASE_URL}/api/system/status`);
    if (!res.ok) throw new Error('Failed to fetch system status');
    return res.json();
  },

  async getScreenshots(): Promise<any[]> {
    const res = await fetch(`${BASE_URL}/api/system/screenshots`);
    if (!res.ok) return [];
    return res.json();
  },

  async openScreenshotsFolder(): Promise<void> {
    await fetch(`${BASE_URL}/api/system/open-screenshots-folder`, { method: 'POST' });
  },

  // History
  async getHistory(limit = 50, search?: string, status?: string): Promise<HistoryItem[]> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (search) params.append('search', search);
    if (status) params.append('status', status);
    const res = await fetch(`${BASE_URL}/api/history?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch history');
    return res.json();
  },

  async clearHistory(): Promise<void> {
    await fetch(`${BASE_URL}/api/history`, { method: 'DELETE' });
  },

  async deleteHistoryItem(id: number): Promise<void> {
    await fetch(`${BASE_URL}/api/history/${id}`, { method: 'DELETE' });
  },

  // Reminders
  async getReminders(includeCompleted = false): Promise<ReminderItem[]> {
    const res = await fetch(`${BASE_URL}/api/reminders?include_completed=${includeCompleted}`);
    if (!res.ok) throw new Error('Failed to fetch reminders');
    return res.json();
  },

  async createReminder(title: string, due_time: string, is_recurring = false, recurrence_pattern?: string): Promise<ReminderItem> {
    const res = await fetch(`${BASE_URL}/api/reminders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, due_time, is_recurring, recurrence_pattern }),
    });
    if (!res.ok) throw new Error('Failed to create reminder');
    return res.json();
  },

  async toggleReminderComplete(id: number): Promise<void> {
    await fetch(`${BASE_URL}/api/reminders/${id}/complete`, { method: 'PATCH' });
  },

  async deleteReminder(id: number): Promise<void> {
    await fetch(`${BASE_URL}/api/reminders/${id}`, { method: 'DELETE' });
  },

  // Applications
  async getApplications(): Promise<AppRegistryItem[]> {
    const res = await fetch(`${BASE_URL}/api/apps`);
    if (!res.ok) throw new Error('Failed to fetch applications');
    return res.json();
  },

  async addApplication(app_key: string, display_name: string, aliases: string[], exec_path: string): Promise<AppRegistryItem> {
    const res = await fetch(`${BASE_URL}/api/apps`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ app_key, display_name, aliases, exec_path }),
    });
    if (!res.ok) throw new Error('Failed to add application');
    return res.json();
  },

  async launchApplication(app_key: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${BASE_URL}/api/apps/launch/${encodeURIComponent(app_key)}`, { method: 'POST' });
    return res.json();
  },

  async deleteApplication(id: number): Promise<void> {
    await fetch(`${BASE_URL}/api/apps/${id}`, { method: 'DELETE' });
  },

  // Analytics
  async getAnalytics(): Promise<AnalyticsData> {
    const res = await fetch(`${BASE_URL}/api/analytics`);
    if (!res.ok) throw new Error('Failed to fetch analytics');
    return res.json();
  },

  // Settings
  async getSettings(): Promise<AppSettings> {
    const res = await fetch(`${BASE_URL}/api/settings`);
    if (!res.ok) throw new Error('Failed to fetch settings');
    return res.json();
  },

  async updateSettings(settings: Partial<AppSettings>): Promise<{ success: boolean; settings: AppSettings }> {
    const res = await fetch(`${BASE_URL}/api/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    if (!res.ok) throw new Error('Failed to update settings');
    return res.json();
  },

  // Help & Demo
  async getHelpGuide(): Promise<HelpCategory[]> {
    const res = await fetch(`${BASE_URL}/api/help`);
    if (!res.ok) return [];
    return res.json();
  },

  async getDemoSamples(): Promise<DemoSample[]> {
    const res = await fetch(`${BASE_URL}/api/demo/samples`);
    if (!res.ok) return [];
    return res.json();
  },

  // Security & Persistent Permissions
  async getSecurityPermissions(): Promise<SecurityPermissionsData> {
    const res = await fetch(`${BASE_URL}/api/security/permissions`);
    if (!res.ok) throw new Error('Failed to fetch security permissions');
    return res.json();
  },

  async grantPermission(scope: string, target = '*', durationDays = 30): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/security/permissions/grant`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope, target, duration_days: durationDays }),
    });
    if (!res.ok) throw new Error('Failed to grant permission');
    return res.json();
  },

  async revokePermission(scope: string, target = '*'): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/security/permissions/revoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope, target }),
    });
    if (!res.ok) throw new Error('Failed to revoke permission');
    return res.json();
  },

  async getAuditLogs(limit = 50): Promise<{ logs: AuditLogEntry[]; count: number }> {
    const res = await fetch(`${BASE_URL}/api/security/audit-logs?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch audit logs');
    return res.json();
  },

  async addAuthorizedDirectory(directory: string): Promise<{ success: boolean; authorized_directories: string[] }> {
    const res = await fetch(`${BASE_URL}/api/security/directories/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ directory }),
    });
    if (!res.ok) throw new Error('Failed to add authorized directory');
    return res.json();
  },

  async removeAuthorizedDirectory(directory: string): Promise<{ success: boolean; authorized_directories: string[] }> {
    const res = await fetch(`${BASE_URL}/api/security/directories/remove`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ directory }),
    });
    if (!res.ok) throw new Error('Failed to remove authorized directory');
    return res.json();
  },

  // Diagnostics
  async runDiagnostics(): Promise<DiagnosticsResult> {
    const res = await fetch(`${BASE_URL}/api/diagnostics/run`);
    if (!res.ok) throw new Error('Failed to run diagnostics');
    return res.json();
  },
};

