import React, { useState, useEffect, useCallback, useRef } from 'react';
import confetti from 'canvas-confetti';

import { Header } from './components/Header';
import { Sidebar, NavTab } from './components/Sidebar';
import { DemoBar } from './components/DemoBar';
import { ConfirmationModal } from './components/ConfirmationModal';
import { DesktopActivityItem } from './components/DesktopActivityPanel';
import { LaunchNotificationPopup, LaunchNotificationData } from './components/LaunchNotificationPopup';

import { Dashboard } from './pages/Dashboard';
import { DemonstrationPage } from './pages/DemonstrationPage';
import { AssistantView } from './pages/AssistantView';
import { HistoryPage } from './pages/HistoryPage';
import { RemindersPage } from './pages/RemindersPage';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SettingsPage } from './pages/SettingsPage';
import { HelpPage } from './pages/HelpPage';
import { DiagnosticsPage } from './pages/DiagnosticsPage';
import { PermissionsPage } from './pages/PermissionsPage';

import { useVoiceRecognition, ListeningMode } from './hooks/useVoiceRecognition';
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
  AgentTaskPlan,
  ContactItem,
} from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [assistantState, setAssistantState] = useState<AssistantState>('idle');
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [conversationHistory, setConversationHistory] = useState<ConversationTurn[]>([]);
  const [lastResult, setLastResult] = useState<CommandExecutionResult | null>(null);
  const [desktopActivities, setDesktopActivities] = useState<DesktopActivityItem[]>([]);
  const [listeningMode, setListeningMode] = useState<ListeningMode>('push_to_talk');
  const [launchNotification, setLaunchNotification] = useState<LaunchNotificationData | null>(null);
  const [activePlan, setActivePlan] = useState<AgentTaskPlan | null>(null);

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
  }, [assistantState]);

  const handleCloseLaunchNotification = useCallback(() => {
    setLaunchNotification(null);
  }, []);

  // Unified Command Result Processing (Voice, Quick Action, Text, or WebSocket)
  const handleCommandResult = useCallback(
    (commandText: string, res: CommandExecutionResult) => {
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

      // 1. Add to Live Conversation Stream
      const userText = commandText || (res.entities?.command_text as string) || (res.data?.original_instruction as string) || 'Voice Command';
      const newTurn: ConversationTurn = {
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        user_text: userText,
        response_text: res.response_text,
        intent: res.intent,
        status: res.status,
        risk_level: res.risk_level,
      };

      setConversationHistory((prev) => [newTurn, ...prev]);
      setAssistantState('speaking');

      // 2. Confetti on successful notable operations
      if (res.success && ['take_screenshot', 'open_application', 'create_folder', 'multi_command_plan', 'search_web'].includes(res.intent)) {
        confetti({ particleCount: 35, spread: 60, origin: { y: 0.8 } });
      }

      // 3. Multi-Command DAG Plan
      if (res.intent === 'multi_command_plan' && res.data) {
        setActivePlan(res.data as AgentTaskPlan);
      }

      const appTask = res.intent === 'multi_command_plan' && res.data?.tasks
        ? res.data.tasks.find((t: any) => t.intent === 'open_application')
        : null;
      const appData = appTask?.data || (res.data && res.data.app_name ? res.data : null);

      // 4. Desktop Activity Tracking for App Launches & Multi-Command Steps
      if (res.intent === 'multi_command_plan' && res.data?.tasks) {
        const newActs: DesktopActivityItem[] = [];
        for (const t of res.data.tasks) {
          const tData = t.data || {};
          const isDone = t.status === 'Completed' || t.status === 'completed';
          if (t.intent === 'open_application') {
            newActs.push({
              id: Math.random().toString(36).substring(2, 9),
              app_key: t.application || 'app',
              app_name: tData.app_name || (t.application ? t.application.toUpperCase() : 'Google Chrome'),
              command_received: userText,
              status: tData.status || (isDone ? 'Window detected' : 'Launch failed'),
              action: tData.action || 'launched_process',
              process_started: tData.process_started ?? isDone,
              window_detected: tData.window_detected ?? isDone,
              pid: tData.pid,
              hwnd: tData.hwnd,
              execution_time_ms: t.execution_time_ms || tData.execution_time_ms,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
              error: t.error || tData.error,
            });
          } else if (t.intent === 'search_web') {
            newActs.push({
              id: Math.random().toString(36).substring(2, 9),
              app_key: 'search',
              app_name: `Google Search: "${t.query || 'query'}"`,
              command_received: userText,
              status: isDone ? 'Completed' : 'Launch failed',
              action: 'executed',
              process_started: true,
              window_detected: true,
              execution_time_ms: t.execution_time_ms || tData.execution_time_ms,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
              error: t.error,
            });
          } else if (t.intent === 'send_message') {
            newActs.push({
              id: Math.random().toString(36).substring(2, 9),
              app_key: 'whatsapp',
              app_name: `WhatsApp: ${t.contact || 'Contact'}`,
              command_received: userText,
              status: isDone ? 'Completed' : 'Launch failed',
              action: 'executed',
              process_started: true,
              window_detected: false,
              execution_time_ms: t.execution_time_ms || tData.execution_time_ms,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
              error: t.error,
            });
          }
        }
        if (newActs.length > 0) {
          setDesktopActivities((prev) => [...newActs, ...prev]);
        }
      } else {
        const appData = res.data && res.data.app_name ? res.data : null;
        if (appData && (appData.app_name || res.entities?.application)) {
          const actItem: DesktopActivityItem = {
            id: Math.random().toString(36).substring(2, 9),
            app_key: appData.app_key || res.entities?.application || 'app',
            app_name: appData.app_name || (res.entities?.application ? res.entities.application.toUpperCase() : 'Application'),
            command_received: userText,
            status: appData.status || (appData.window_detected ? 'Window detected' : 'Process started'),
            action: appData.action || 'launched_process',
            process_started: appData.process_started ?? true,
            window_detected: appData.window_detected ?? false,
            pid: appData.pid,
            hwnd: appData.hwnd,
            execution_time_ms: appData.execution_time_ms ?? res.execution_time_ms,
            timestamp: appData.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            error: appData.error,
          };
          setDesktopActivities((prev) => [actItem, ...prev]);
        }
      }

      // 5. High-Visibility Popup Notification Toast
      const rawApp = (appTask?.application || res.entities?.application || appData?.app_key || '').toLowerCase();
      const appDisplayName = appData?.app_name || (rawApp ? rawApp.charAt(0).toUpperCase() + rawApp.slice(1) : '');

      let toastTitle = appDisplayName;
      let toastMessage = res.response_text;
      const isSuccess = Boolean(
        res.success ||
        (appTask && (String(appTask.status).toLowerCase() === 'completed' || appTask.data?.success))
      );
      let toastStatus = appData?.status || (isSuccess ? 'Window detected' : 'Launch failed');

      if (res.intent === 'open_application' || appTask) {
        toastTitle = appDisplayName || 'Application';
        toastMessage = isSuccess ? `${toastTitle} successfully opened.` : `Failed to launch ${toastTitle}.`;
        toastStatus = appData?.status || (isSuccess ? 'Window detected' : 'Launch failed');
      } else if (res.intent === 'multi_command_plan') {
        toastTitle = appDisplayName ? `${appDisplayName} + Search` : 'Multi-Command Agent';
        toastMessage = res.response_text || 'Multi-command execution finished.';
        toastStatus = res.status === 'success' || isSuccess ? 'Completed' : 'Partially Failed';
      } else if (res.intent === 'search_web') {
        toastTitle = 'Web Search';
        toastMessage = res.response_text || `Searched for ${res.entities?.query || 'query'}`;
        toastStatus = 'Completed';
      } else {
        toastTitle = res.intent.replace(/_/g, ' ').toUpperCase();
        toastMessage = res.response_text || 'Command completed.';
        toastStatus = res.success ? 'Success' : 'Failed';
      }

      setLaunchNotification({
        isOpen: true,
        appName: toastTitle,
        message: toastMessage,
        status: toastStatus,
        executionTimeMs: appData?.execution_time_ms ?? res.execution_time_ms ?? 0,
        isSuccess: isSuccess,
        error: appData?.error || (!res.success ? res.response_text : null),
        protocol: appData?.client_protocol,
        webFallback: appData?.web_fallback,
        rawApp: rawApp,
      });

      // 6. Search Web Tab Opening
      const searchTask = res.intent === 'multi_command_plan' && res.data?.tasks
        ? res.data.tasks.find((t: any) => t.intent === 'search_web')
        : null;

      if (searchTask && (String(searchTask.status).toLowerCase() === 'completed' || searchTask.data?.success)) {
        const searchUrl = searchTask.data?.url || `https://www.google.com/search?q=${encodeURIComponent(searchTask.query || '')}`;
        try {
          window.open(searchUrl, '_blank');
        } catch (e) {
          console.debug('Search popup notice:', e);
        }
      } else if (res.intent === 'search_web' && res.success) {
        const searchUrl = res.data?.url || `https://www.google.com/search?q=${encodeURIComponent(res.entities?.query || '')}`;
        try {
          window.open(searchUrl, '_blank');
        } catch (e) {
          console.debug('Search popup notice:', e);
        }
      }

      // 7. Client-side Application Launching (enables real desktop apps to open even when connected to Render cloud)
      if ((res.intent === 'open_application' || appTask) && isSuccess) {
        try {
          if (rawApp.includes('chrome') || rawApp.includes('browser')) {
            if (!searchTask) window.open('https://www.google.com', '_blank');
          } else if (rawApp.includes('calc')) {
            const link = document.createElement('a');
            link.href = 'calculator:';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          } else if (rawApp.includes('whatsapp')) {
            const link = document.createElement('a');
            link.href = 'whatsapp:';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          } else if (rawApp.includes('code') || rawApp.includes('vs')) {
            const link = document.createElement('a');
            link.href = 'vscode:';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          } else if (rawApp.includes('spotify')) {
            const link = document.createElement('a');
            link.href = 'spotify:';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          } else if (appData?.client_protocol) {
            const link = document.createElement('a');
            link.href = appData.client_protocol;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          } else if (appData?.web_fallback) {
            window.open(appData.web_fallback, '_blank');
          }
        } catch (launchErr) {
          console.debug('Client protocol launch notice:', launchErr);
        }
      }

      // Return to listening if continuous listening mode, else idle
      setTimeout(() => {
        setAssistantState((prev) => (prev === 'speaking' ? 'idle' : prev));
      }, 2500);

      // Refresh reminders or system if relevant
      if (['set_reminder', 'list_reminders'].includes(res.intent)) {
        api.getReminders().then(setReminders).catch(() => {});
      }
    },
    []
  );

  // Execute Command Pipeline
  const executeCommand = useCallback(
    async (commandText: string) => {
      if (!commandText.trim()) return;

      setAssistantState('processing');

      try {
        const res = await api.processCommand(commandText, {
          demo_mode: settings.demo_mode,
        });

        handleCommandResult(commandText, res);
      } catch (err: any) {
        setAssistantState('error');
        setTimeout(() => setAssistantState('idle'), 3000);
      }
    },
    [handleCommandResult, settings.demo_mode]
  );

  // Upgraded Voice Recognition hook with persistent streaming & modes
  const {
    isListening,
    isProcessing: sttProcessing,
    transcript,
    lastRecognizedCommand,
    audioLevel,
    listeningDuration,
    connectionStatus,
    errorMessage,
    startListening,
    stopListening,
  } = useVoiceRecognition({
    wakeWord: settings.wake_word,
    wakeWordEnabled: settings.wake_word_enabled,
    language: settings.default_language,
    mode: listeningMode,
    onCommandDetected: (text) => {
      executeCommand(text);
    },
    onError: (err) => {
      console.warn('Voice recognition error:', err);
      setAssistantState('error');
      setTimeout(() => setAssistantState('idle'), 2500);
    },
  });

  // Keep assistantState synchronized with listening status
  useEffect(() => {
    if (isListening) {
      setAssistantState('listening');
    } else if (sttProcessing) {
      setAssistantState('processing');
    }
  }, [isListening, sttProcessing]);

  // Robust Voice Toggle
  const handleToggleMic = () => {
    if (assistantState === 'speaking') {
      handleStopVoice();
      return;
    }

    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  // WebSocket hook for real-time state, reminders, desktop activity, and AI Agent progress
  useWebSocket({
    onStateChange: (state) => {
      setAssistantState(state);
    },
    onReminderAlert: (data) => {
      alert(`⏰ Reminder: ${data.title}`);
      api.getReminders().then(setReminders).catch(() => {});
    },
    onCommandResult: (res) => {
      handleCommandResult(res.entities?.command_text || 'Voice Command', res);
    },
    onDesktopActivity: (act) => {
      if (act && act.app_name) {
        setDesktopActivities((prev) => [act, ...prev]);
      }
    },
    onAiAgentActivity: (plan) => {
      setActivePlan(plan);
    },
    onAgentTaskProgress: (data) => {
      setActivePlan((prev) => {
        if (!prev || prev.plan_id !== data.plan_id) return prev;
        return {
          ...prev,
          tasks: prev.tasks.map((t) => (t.id === data.task.id ? data.task : t)),
        };
      });
    },
    onTaskEvent: (event) => {
      if (!event) return;
      const isFailed = event.status === 'Failed' || event.status === 'Partially Failed';
      setLaunchNotification({
        isOpen: true,
        appName: event.metadata?.application || event.metadata?.app_name || event.title,
        title: event.title,
        message: event.message || `Status: ${event.status}`,
        status: event.status,
        isSuccess: !isFailed,
        error: isFailed ? event.message : undefined,
        eventType: event.event_type,
        rawApp: event.metadata?.application,
      });
    },
  });

  const handleConfirmPlan = async (planId: string, confirmationId?: string) => {
    try {
      const res = await api.confirmAgentPlan({ plan_id: planId, confirmation_id: confirmationId, approved: true });
      if (res) {
        setActivePlan(res);
      }
    } catch (e) {
      console.error('Error confirming plan:', e);
    }
  };

  const handleCancelPlan = async (planId: string) => {
    try {
      const res = await api.confirmAgentPlan({ plan_id: planId, approved: false });
      if (res) {
        setActivePlan(res);
      }
    } catch (e) {
      console.error('Error cancelling plan:', e);
    }
  };

  const handleSelectContact = (contact: ContactItem) => {
    executeCommand(contact.name);
  };

  const handleRetryTask = (taskId: string) => {
    if (activePlan) {
      executeCommand(activePlan.original_instruction);
    }
  };

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
              devices={audioDevices}
              selectedDeviceId={selectedDeviceId}
              onSelectDevice={handleSelectDevice}
              latencyMetrics={latestMetrics}
              listeningMode={listeningMode}
              onToggleListeningMode={setListeningMode}
              listeningDuration={listeningDuration}
              connectionStatus={connectionStatus}
              lastRecognizedCommand={lastRecognizedCommand}
              errorMessage={errorMessage}
              desktopActivities={desktopActivities}
              onClearActivities={() => setDesktopActivities([])}
              activePlan={activePlan}
              onConfirmPlan={handleConfirmPlan}
              onCancelPlan={handleCancelPlan}
              onRetryTask={handleRetryTask}
              onSelectContact={handleSelectContact}
              lastResult={lastResult}
            />
          )}

          {activeTab === 'demonstration' && (
            <div className="p-6">
              <DemonstrationPage
                assistantState={assistantState}
                onToggleMic={handleToggleMic}
                onStopVoice={handleStopVoice}
                transcript={transcript}
                lastResult={lastResult}
                onExecuteCommand={executeCommand}
                audioLevel={audioLevel}
                listeningMode={listeningMode}
                onToggleListeningMode={setListeningMode}
                listeningDuration={listeningDuration}
                connectionStatus={connectionStatus}
                lastRecognizedCommand={lastRecognizedCommand}
                errorMessage={errorMessage}
                desktopActivities={desktopActivities}
                onClearActivities={() => setDesktopActivities([])}
                activePlan={activePlan}
                onConfirmPlan={handleConfirmPlan}
                onCancelPlan={handleCancelPlan}
                onRetryTask={handleRetryTask}
                onSelectContact={handleSelectContact}
              />
            </div>
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
              micMode="browser"
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

      {/* Application Launch Confirmation Popup Notification Toast */}
      <LaunchNotificationPopup
        notification={launchNotification}
        onClose={handleCloseLaunchNotification}
        onRetry={(name) => executeCommand(`Open ${name}`)}
      />
    </div>
  );
}
export default App;
