import React from 'react';
import {
  Monitor,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCw,
  ExternalLink,
  Layers,
  Clock,
  Hash,
  Trash2,
} from 'lucide-react';

export interface DesktopActivityItem {
  id?: string;
  app_key: string;
  app_name: string;
  command_received: string;
  status: string; // 'Window detected' | 'Process started' | 'Launch failed'
  action: string; // 'brought_to_foreground' | 'launched_process' | 'failed'
  process_started: boolean;
  window_detected: boolean;
  pid?: number | null;
  hwnd?: number | null;
  execution_time_ms?: number;
  timestamp: string;
  error?: string | null;
}

interface DesktopActivityPanelProps {
  activities: DesktopActivityItem[];
  onClearActivities?: () => void;
  className?: string;
}

export const DesktopActivityPanel: React.FC<DesktopActivityPanelProps> = ({
  activities,
  onClearActivities,
  className = '',
}) => {
  const getAppIcon = (appKey: string) => {
    const key = appKey.toLowerCase();
    if (key.includes('chrome') || key.includes('browser')) {
      return (
        <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 font-bold text-xs">
          CR
        </div>
      );
    }
    if (key.includes('whatsapp')) {
      return (
        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold text-xs">
          WA
        </div>
      );
    }
    if (key.includes('calc')) {
      return (
        <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 font-bold text-xs">
          CA
        </div>
      );
    }
    if (key.includes('note')) {
      return (
        <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 font-bold text-xs">
          NP
        </div>
      );
    }
    if (key.includes('code') || key.includes('vs')) {
      return (
        <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 font-bold text-xs">
          VS
        </div>
      );
    }
    return (
      <div className="w-8 h-8 rounded-lg bg-slate-700/50 border border-slate-600 flex items-center justify-center text-slate-300 font-bold text-xs">
        <Monitor className="w-4 h-4 text-cyan-400" />
      </div>
    );
  };

  const getStatusBadge = (item: DesktopActivityItem) => {
    if (item.window_detected) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 border border-emerald-500/40 text-emerald-300">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          <span>Window detected</span>
        </span>
      );
    }
    if (item.process_started) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950/80 border border-blue-500/40 text-blue-300">
          <Play className="w-3 h-3 text-blue-400" />
          <span>Process started</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950/80 border border-rose-500/40 text-rose-300">
        <AlertTriangle className="w-3 h-3 text-rose-400" />
        <span>Launch failed</span>
      </span>
    );
  };

  const getActionBadge = (action: string) => {
    if (action === 'brought_to_foreground') {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] text-cyan-300 bg-cyan-950/50 border border-cyan-800/60 px-2 py-0.5 rounded">
          <Layers className="w-3 h-3 text-cyan-400" /> Foreground Activated
        </span>
      );
    }
    if (action === 'launched_process') {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] text-indigo-300 bg-indigo-950/50 border border-indigo-800/60 px-2 py-0.5 rounded">
          <ExternalLink className="w-3 h-3 text-indigo-400" /> New Process Launched
        </span>
      );
    }
    return (
      <span className="text-[11px] text-slate-400">
        {action}
      </span>
    );
  };

  return (
    <div className={`bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-md ${className}`}>
      {/* Panel Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 border border-cyan-500/30">
            <Monitor className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-100 text-base flex items-center gap-2">
              Desktop Activity
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-normal">
                Live Window Tracker
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Verified OS process execution & foreground window status
            </p>
          </div>
        </div>

        {activities.length > 0 && onClearActivities && (
          <button
            type="button"
            onClick={onClearActivities}
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition px-2.5 py-1 rounded-lg hover:bg-slate-800 border border-transparent hover:border-slate-700"
            title="Clear activity log"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear</span>
          </button>
        )}
      </div>

      {/* Activities List */}
      {activities.length === 0 ? (
        <div className="text-center py-8 text-slate-500 text-xs">
          <Monitor className="w-8 h-8 mx-auto mb-2 opacity-30 text-slate-400" />
          No desktop applications launched in this session yet.
          <p className="mt-1 text-slate-600">
            Say <span className="text-cyan-400 font-mono">"Open Chrome"</span> or <span className="text-cyan-400 font-mono">"Open Calculator"</span> to see live desktop activity.
          </p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
          {activities.map((item, idx) => (
            <div
              key={item.id || idx}
              className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition flex flex-col md:flex-row md:items-center justify-between gap-3"
            >
              {/* App info */}
              <div className="flex items-center gap-3">
                {getAppIcon(item.app_key)}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-100 text-sm">
                      {item.app_name}
                    </span>
                    {getActionBadge(item.action)}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    Command: <span className="text-slate-300 font-mono">"{item.command_received}"</span>
                  </div>
                </div>
              </div>

              {/* Status and telemetry */}
              <div className="flex items-center gap-3 flex-wrap md:flex-nowrap justify-between md:justify-end">
                {/* Status badge: Window detected vs Process started */}
                {getStatusBadge(item)}

                {/* Technical details pill: PID, HWND, Execution Duration */}
                <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400 bg-slate-900 px-2.5 py-1 rounded-lg border border-slate-800">
                  {item.pid && (
                    <span title="Process ID" className="flex items-center gap-0.5">
                      <Hash className="w-3 h-3 text-cyan-400" />
                      PID: <strong className="text-slate-200">{item.pid}</strong>
                    </span>
                  )}
                  {item.execution_time_ms !== undefined && (
                    <span title="Execution Duration" className="flex items-center gap-0.5">
                      <Clock className="w-3 h-3 text-purple-400" />
                      {item.execution_time_ms}ms
                    </span>
                  )}
                  <span className="text-slate-500">
                    {item.timestamp}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
