import React, { useState, useEffect, useCallback } from 'react';
import confetti from 'canvas-confetti';

import { Header } from './components/Header';
import { Sidebar, NavTab } from './components/Sidebar';
import { DemoBar } from './components/DemoBar';
import { ConfirmationModal } from './components/ConfirmationModal';

import { Dashboard } from './pages/Dashboard';
import { AssistantView } from './pages/AssistantView';
import { HistoryPage } from './pages/HistoryPage';
import { RemindersPage } from './pages/RemindersPage';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SettingsPage } from './pages/SettingsPage';
import { HelpPage } from './pages/HelpPage';
import { DiagnosticsPage } from './pages/DiagnosticsPage';
import { PermissionsPage } from './pages/PermissionsPage';

import { useVoiceRecognition } from './hooks/useVoiceRecognition';
import { useWebSocket } from './hooks/useWebSocket';
import { api } from './services/api';

import {
  AssistantState,
  ConversationTurn,
  SystemStatus,
  ReminderItem,
  CommandExecutionResult,
  AppSettings,
  AudioDeviceItem,
  LatencyMetrics,
} from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [assistantState, setAssistantState] = useState<AssistantState>('idle');
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [conversationHistory, setConversationHistory] = useState<ConversationTurn[]>([]);
  const [lastResult, setLastResult] = useState<CommandExecutionResult | null>(null);

  // Audio Hardware Devices & Latency metrics
  const [audioDevices, setAudioDevices] = useState<AudioDeviceItem[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null);
  const [latestMetrics, setLatestMetrics] = useState<LatencyMetrics | null>(null);


  // Settings
  const [settings, setSettings] = useState<AppSettings>({
    app_name: 'Aura Voice Assistant',
    wake_word: 'hey assistant',
    wake_word_enabled: true,
    default_language: 'en',
    tts_rate: 180,
    tts_volume: 0.9,
    clipboard_permission_enabled: true,
    require_confirmation_high_risk: true,
    require_confirmation_med_risk: true,
    demo_mode: false,
    default_browser: 'default',
    default_music_app: 'default',
    theme: 'dark',
    has_openai_key: false,
  });

  // Confirmation Modal state
  const [confirmationState, setConfirmationState] = useState<{
    isOpen: boolean;
    confirmationId: string;
    prompt: string;
    intent: string;
    riskLevel: 'medium' | 'high';
  }>({
    isOpen: false,
    confirmationId: '',
    prompt: '',
    intent: '',
    riskLevel: 'high',
  });

  // Fetch initial data
  const loadInitialData = useCallback(async () => {
    try {
      const [sData, rData, stData, dData] = await Promise.all([
        api.getSettings(),
        api.getReminders(false),
        api.getSystemStatus(),
        api.getAudioDevices().catch(() => ({ devices: [], selected_device_id: null })),
      ]);
      setSettings(sData);
      setReminders(rData);
      setSystemStatus(stData);
      if (dData && dData.devices) {
        setAudioDevices(dData.devices);
        setSelectedDeviceId(dData.selected_device_id);
      }
    } catch (e) {
      console.warn('Initial data load error:', e);
    }
  }, []);

  useEffect(() => {
    loadInitialData();

    // Poll system status every 6 seconds
    const interval = setInterval(() => {
      api.getSystemStatus().then(setSystemStatus).catch(() => {});
    }, 6000);

    return () => clearInterval(interval);
  }, [loadInitialData]);

  const handleSelectDevice = async (id: number) => {
    try {
      await api.selectAudioDevice(id);
      setSelectedDeviceId(id);
      const d = await api.getAudioDevices();
      setAudioDevices(d.devices);
    } catch (e) {
      console.warn('Device select error:', e);
    }
  };

  const handleStopVoice = async () => {
    try {
      await api.stopVoice();
      setAssistantState('idle');
    } catch (e) {
      setAssistantState('idle');
    }
  };

  // Keyboard shortcut listener (Esc to stop speaking, Ctrl+Space for voice toggle)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && assistantState === 'speaking') {
        handleStopVoice();
      } else if (e.code === 'Space' && e.ctrlKey) {
        e.preventDefault();
        handleToggleMic();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [assistantState, selectedDeviceId]);

  // Execute Command Pipeline
  const executeCommand = useCallback(
    async (commandText: string) => {
      if (!commandText.trim()) return;

      setAssistantState('processing');

      try {
        const res = await api.processCommand(commandText, {
          demo_mode: settings.demo_mode,
        });

        setLastResult(res);

        if (res.requires_confirmation && res.confirmation_id) {
          setAssistantState('waiting_confirmation');
          setConfirmationState({
            isOpen: true,
            confirmationId: res.confirmation_id,
            prompt: res.response_text,
            intent: res.intent,
            riskLevel: res.risk_level as 'medium' | 'high',
          });
          return;
        }

        // Add to live conversation stream
        const newTurn: ConversationTurn = {
          id: Math.random().toString(36).substring(2, 9),
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          user_text: commandText,
          response_text: res.response_text,
          intent: res.intent,
          status: res.status,
          risk_level: res.risk_level,
        };

        setConversationHistory((prev) => [newTurn, ...prev]);
        setAssistantState('speaking');

        if (res.success && ['take_screenshot', 'open_application', 'create_folder'].includes(res.intent)) {
          confetti({ particleCount: 35, spread: 60, origin: { y: 0.8 } });
        }

        // Return to idle after speech
        setTimeout(() => setAssistantState('idle'), 2500);

        // Refresh reminders or system if relevant
        if (['set_reminder', 'list_reminders'].includes(res.intent)) {
          api.getReminders().then(setReminders).catch(() => {});
        }
      } catch (err: any) {
        setAssistantState('error');
        setTimeout(() => setAssistantState('idle'), 3000);
      }
    },
    [settings.demo_mode]
  );

  // Handle Voice Recognition hook
  const {
    isListening,
    isProcessing: sttProcessing,
    transcript,
    audioLevel,
    startListening,
    stopListening,
  } = useVoiceRecognition({
    wakeWord: settings.wake_word,
    wakeWordEnabled: settings.wake_word_enabled,
    language: settings.default_language,
    onCommandDetected: (text) => {
      executeCommand(text);
    },
    onError: (err) => {
      console.warn('Voice recognition error:', err);
      setAssistantState('error');
      setTimeout(() => setAssistantState('idle'), 2500);
    },
  });

  const [micMode, setMicMode] = useState<'desktop' | 'browser'>('desktop');

  // Keep assistantState in sync with listening
  useEffect(() => {
    if (isListening) {
      setAssistantState('listening');
    } else if (sttProcessing) {
      setAssistantState('processing');
    }
  }, [isListening, sttProcessing]);

  const handleToggleMic = async () => {
    if (assistantState === 'speaking') {
      handleStopVoice();
      return;
    }

    if (micMode === 'desktop') {
      if (assistantState === 'listening') return;
      setAssistantState('listening');
      try {
        const res = await api.listenDesktopMic({
          duration: 4.0,
          use_vad: true,
          device_id: selectedDeviceId ?? undefined,
          auto_execute: true,
        });

        if (res.metrics) {
          setLatestMetrics(res.metrics);
        }

        if (res.success && res.text) {
          if (res.execution) {
            setLastResult(res.execution);
            const newTurn: ConversationTurn = {
              id: Math.random().toString(36).substring(2, 9),
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              user_text: res.text,
              response_text: res.execution.response_text,
              intent: res.execution.intent,
              status: res.execution.status,
              risk_level: res.execution.risk_level,
            };
            setConversationHistory((prev) => [newTurn, ...prev]);
            setAssistantState('speaking');
            setTimeout(() => setAssistantState('idle'), 2500);
          } else {
            executeCommand(res.text);
          }
        } else {
          setAssistantState('error');
          setTimeout(() => setAssistantState('idle'), 2500);
        }
      } catch (e) {
        setAssistantState('error');
        setTimeout(() => setAssistantState('idle'), 2500);
      }
    } else {
      if (isListening) {
        stopListening();
      } else {
        startListening();
      }
    }
  };

  // WebSocket hook for real-time states and reminders
  useWebSocket({
    onStateChange: (state) => {
      setAssistantState(state);
    },
    onReminderAlert: (data) => {
      alert(`⏰ Reminder: ${data.title}`);
      api.getReminders().then(setReminders).catch(() => {});
    },
    onCommandResult: (res) => {
      setLastResult(res);
    },
  });

  // Confirmation handlers
  const handleConfirmAction = async (approved: boolean) => {
    const { confirmationId } = confirmationState;
    setConfirmationState((prev) => ({ ...prev, isOpen: false }));
    setAssistantState('executing');

    try {
      const res = await api.confirmCommand(confirmationId, approved);
      setLastResult(res);

      const turn: ConversationTurn = {
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        user_text: `Confirmation: ${approved ? 'Approved' : 'Rejected'}`,
        response_text: res.response_text,
        intent: res.intent,
        status: res.status,
        risk_level: res.risk_level,
      };

      setConversationHistory((prev) => [turn, ...prev]);
      setAssistantState('speaking');
      setTimeout(() => setAssistantState('idle'), 2500);
    } catch (e) {
      setAssistantState('error');
      setTimeout(() => setAssistantState('idle'), 2500);
    }
  };

  const handleSpeakText = (text: string) => {
    api.speakText(text);
  };

  const handleToggleTheme = () => {
    const newTheme = settings.theme === 'dark' ? 'light' : 'dark';
    setSettings((prev) => ({ ...prev, theme: newTheme }));
    api.updateSettings({ theme: newTheme });
  };

  const handleToggleLanguage = () => {
    const newLang = settings.default_language === 'en' ? 'hi' : 'en';
    setSettings((prev) => ({ ...prev, default_language: newLang }));
    api.updateSettings({ default_language: newLang });
  };

  return (
    <div className={`min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans ${settings.theme === 'dark' ? 'dark' : ''}`}>
      {/* Top Header */}
      <Header
        assistantName={settings.app_name}
        assistantState={assistantState}
        isOnline={systemStatus?.is_online ?? true}
        theme={settings.theme}
        onToggleTheme={handleToggleTheme}
        language={settings.default_language}
        onToggleLanguage={handleToggleLanguage}
        onOpenSettings={() => setActiveTab('settings')}
      />

      {/* Interactive Demo Showcase Bar */}
      <DemoBar onRunSample={executeCommand} />

      {/* Main Layout Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Navigation Sidebar */}
        <Sidebar
          currentTab={activeTab}
          onTabChange={setActiveTab}
          pendingRemindersCount={reminders.length}
        />

        {/* Dynamic Viewport Content */}
        <main className="flex-1 overflow-y-auto">
          {activeTab === 'dashboard' && (
            <Dashboard
              assistantState={assistantState}
              onToggleMic={handleToggleMic}
              onStopVoice={handleStopVoice}
              audioLevel={audioLevel}
              transcript={transcript}
              assistantName={settings.app_name}
              conversationHistory={conversationHistory}
              systemStatus={systemStatus}
              reminders={reminders}
              onExecuteCommand={executeCommand}
              onSpeakText={handleSpeakText}
              micMode={micMode}
              onToggleMicMode={setMicMode}
              devices={audioDevices}
              selectedDeviceId={selectedDeviceId}
              onSelectDevice={handleSelectDevice}
              latencyMetrics={latestMetrics}
            />
          )}

          {activeTab === 'assistant' && (
            <AssistantView
              assistantState={assistantState}
              onToggleMic={handleToggleMic}
              onStopVoice={handleStopVoice}
              audioLevel={audioLevel}
              transcript={transcript}
              assistantName={settings.app_name}
              lastResult={lastResult}
              onSpeakText={handleSpeakText}
              micMode={micMode}
              onToggleMicMode={setMicMode}
              devices={audioDevices}
              selectedDeviceId={selectedDeviceId}
              onSelectDevice={handleSelectDevice}
              latencyMetrics={latestMetrics}
            />
          )}

          {activeTab === 'diagnostics' && <DiagnosticsPage />}

          {activeTab === 'permissions' && <PermissionsPage />}

          {activeTab === 'history' && <HistoryPage />}

          {activeTab === 'reminders' && <RemindersPage />}

          {activeTab === 'apps' && <ApplicationsPage />}

          {activeTab === 'analytics' && <AnalyticsPage />}

          {activeTab === 'settings' && (
            <SettingsPage
              onSettingsSaved={(newS) => setSettings(newS)}
            />
          )}

          {activeTab === 'help' && (
            <HelpPage onRunCommand={(cmd) => {
              setActiveTab('dashboard');
              executeCommand(cmd);
            }} />
          )}
        </main>
      </div>

      {/* Security Confirmation Modal */}
      <ConfirmationModal
        isOpen={confirmationState.isOpen}
        prompt={confirmationState.prompt}
        intent={confirmationState.intent}
        riskLevel={confirmationState.riskLevel}
        onConfirm={() => handleConfirmAction(true)}
        onCancel={() => handleConfirmAction(false)}
      />
    </div>
  );
}
export default App;
