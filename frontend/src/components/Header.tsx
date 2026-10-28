import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Wifi,
  WifiOff,
  Mic,
  MicOff,
  Sun,
  Moon,
  Globe,
  Settings as SettingsIcon,
} from 'lucide-react';
import { AssistantState } from '../types';

interface HeaderProps {
  assistantName: string;
  assistantState: AssistantState;
  isOnline: boolean;
  theme: string;
  onToggleTheme: () => void;
  language: string;
  onToggleLanguage: () => void;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  assistantName,
  assistantState,
  isOnline,
  theme,
  onToggleTheme,
  language,
  onToggleLanguage,
  onOpenSettings,
}) => {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formattedDate = currentTime.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  const formattedTime = currentTime.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  return (
    <header className="w-full bg-slate-900/95 dark:bg-slate-900/95 border-b border-slate-800 px-6 py-3.5 flex items-center justify-between text-white backdrop-blur-md sticky top-0 z-40">
      {/* Brand & Assistant Name */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/25 ring-1 ring-white/20">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-base md:text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-300">
              {assistantName}
            </h1>
            <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
              AI Voice v1.0
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            Intelligent Desktop Assistant
          </p>
        </div>
      </div>

      {/* Date, Time & Status Indicators */}
      <div className="flex items-center gap-3 md:gap-5">
        {/* Live Clock */}
        <div className="hidden sm:flex flex-col items-end text-right">
          <span className="text-xs font-semibold text-slate-200 font-mono tracking-wide">
            {formattedTime}
          </span>
          <span className="text-[11px] text-slate-400">
            {formattedDate}
          </span>
        </div>

        <div className="h-6 w-px bg-slate-800 hidden sm:block" />

        {/* Online / Offline Status */}
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${isOnline ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25' : 'bg-rose-500/10 text-rose-400 border-rose-500/25'}`}>
          {isOnline ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          <span className="hidden md:inline">{isOnline ? 'Online' : 'Offline Mode'}</span>
        </div>

        {/* Mic Status */}
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${assistantState === 'listening' ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30 animate-pulse' : 'bg-slate-800 text-slate-400 border-slate-700/60'}`}>
          {assistantState === 'listening' ? <Mic className="w-3.5 h-3.5" /> : <MicOff className="w-3.5 h-3.5" />}
          <span className="capitalize">{assistantState}</span>
        </div>

        {/* Language Switcher */}
        <button
          onClick={onToggleLanguage}
          className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium transition"
          title="Switch Language: English / Hindi"
        >
          <Globe className="w-3.5 h-3.5 text-blue-400" />
          <span className="uppercase font-bold">{language}</span>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={onToggleTheme}
          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
          title="Toggle Theme"
        >
          {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-400" />}
        </button>

        {/* Settings button */}
        <button
          onClick={onOpenSettings}
          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
          title="Open Settings"
        >
          <SettingsIcon className="w-4 h-4 text-slate-300 hover:text-white" />
        </button>
      </div>
    </header>
  );
};
