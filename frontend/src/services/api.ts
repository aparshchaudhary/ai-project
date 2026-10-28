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
  async listenDesktopMic(duration = 4.0): Promise<{ success: boolean; text: string; error?: string; execution?: CommandExecutionResult }> {
    const res = await fetch(`${BASE_URL}/api/voice/listen-desktop?duration=${duration}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Desktop mic recording failed');
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
};
