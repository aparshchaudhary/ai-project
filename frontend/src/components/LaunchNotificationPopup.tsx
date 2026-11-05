import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  ExternalLink,
  RotateCw,
  X,
  Play,
  Monitor,
  Search,
  MessageCircle,
  Sparkles,
} from 'lucide-react';

export interface LaunchNotificationData {
  isOpen: boolean;
  appName: string;
  title?: string;
  message: string;
  status: string; // 'Received' | 'In Progress' | 'Completed' | 'Window detected' | 'Process started' | 'Launch failed' | 'Partially Failed' | 'Failed'
  executionTimeMs?: number;
  isSuccess: boolean;
  error?: string | null;
  protocol?: string | null;
  webFallback?: string | null;
  rawApp?: string;
  eventType?: string;
}

interface LaunchNotificationPopupProps {
  notification: LaunchNotificationData | null;
  onClose: () => void;
  onRetry?: (appName: string) => void;
}

export const LaunchNotificationPopup: React.FC<LaunchNotificationPopupProps> = ({
  notification,
  onClose,
  onRetry,
}) => {
  const [progress, setProgress] = useState(100);
  const onCloseRef = React.useRef(onClose);

  React.useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!notification || !notification.isOpen) {
      setProgress(100);
      return;
    }

    // Do NOT auto-dismiss if currently In Progress or Received
    if (notification.status === 'In Progress' || notification.status === 'Received') {
      setProgress(100);
      return;
    }

    setProgress(100);
    const duration = 6500; // 6.5s auto-dismiss on completion/failure
    const interval = 50;
    const step = (interval / duration) * 100;

    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev <= step) {
          clearInterval(timer);
          if (onCloseRef.current) onCloseRef.current();
          return 0;
        }
        return prev - step;
      });
    }, interval);

    return () => clearInterval(timer);
  }, [notification]);

  if (!notification || !notification.isOpen) return null;

  const {
    appName,
    title,
    message,
    status,
    executionTimeMs,
    isSuccess,
    error,
    protocol,
    webFallback,
    rawApp,
    eventType,
  } = notification;

  const isInProgress = status === 'In Progress' || status === 'Received';
  const isFailed = status === 'Failed' || status === 'Launch failed' || status === 'Partially Failed' || !isSuccess;

  // Direct user-gesture click handler that bypasses browser popup blockers
  const handlePopUpDirectly = () => {
    const target = (rawApp || appName).toLowerCase();
    try {
      if (target.includes('chrome') || target.includes('browser')) {
        window.open('https://www.google.com', '_blank');
      } else if (target.includes('calc')) {
        const link = document.createElement('a');
        link.href = 'calculator:';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else if (target.includes('whatsapp')) {
        const link = document.createElement('a');
        link.href = 'whatsapp:';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else if (target.includes('code') || target.includes('vs')) {
        const link = document.createElement('a');
        link.href = 'vscode:';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else if (target.includes('spotify')) {
        const link = document.createElement('a');
        link.href = 'spotify:';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else if (protocol) {
        const link = document.createElement('a');
        link.href = protocol;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else if (webFallback) {
        window.open(webFallback, '_blank');
      }
    } catch (e) {
      console.debug('Direct popup trigger notice:', e);
    }
  };

  const getStatusBadge = () => {
    if (status === 'Completed' || status === 'Window detected') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 border border-emerald-500/40 text-emerald-300">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>Completed</span>
        </span>
      );
    }
    if (isInProgress) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/80 border border-amber-500/40 text-amber-300">
          <RotateCw className="w-3.5 h-3.5 text-amber-400 animate-spin" />
          <span>{status}</span>
        </span>
      );
    }
    if (status === 'Process started' || isSuccess) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950/80 border border-blue-500/40 text-blue-300">
          <Play className="w-3.5 h-3.5 text-blue-400" />
          <span>Process started</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950/80 border border-rose-500/40 text-rose-300">
        <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
        <span>{status || 'Launch failed'}</span>
      </span>
    );
  };

  const getHeaderIcon = () => {
    if (isInProgress) {
      return <RotateCw className="w-6 h-6 animate-spin text-amber-400" />;
    }
    if (!isFailed) {
      return <CheckCircle2 className="w-6 h-6 animate-pulse text-emerald-400" />;
    }
    return <AlertTriangle className="w-6 h-6 text-rose-400" />;
  };

  const getCategoryLabel = () => {
    if (eventType === 'command_received') return 'Command Received';
    if (eventType === 'workflow_completed' || eventType === 'workflow_partial_failure') return 'Workflow Summary';
    if (title && (title.includes('Search') || title.includes('search'))) return 'Web Search';
    return 'Desktop Task';
  };

  return (
    <div className="fixed bottom-6 right-6 z-[9999] max-w-sm w-full animate-bounce-short select-none">
      <div
        className={`relative overflow-hidden rounded-2xl p-5 shadow-2xl backdrop-blur-xl border transition-all duration-300 ${
          isInProgress
            ? 'bg-slate-900/95 border-amber-500/40 shadow-amber-950/30 ring-1 ring-amber-500/30'
            : !isFailed
            ? 'bg-slate-900/95 border-emerald-500/40 shadow-emerald-950/30 ring-1 ring-emerald-500/30'
            : 'bg-slate-900/95 border-rose-500/40 shadow-rose-950/30 ring-1 ring-rose-500/30'
        }`}
      >
        {/* Top Dismiss Progress Line */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-slate-800">
          <div
            className={`h-full transition-all duration-75 ${
              isInProgress
                ? 'bg-gradient-to-r from-amber-500 to-yellow-400 animate-pulse'
                : !isFailed
                ? 'bg-gradient-to-r from-emerald-500 to-cyan-400'
                : 'bg-gradient-to-r from-rose-500 to-red-400'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Header Row */}
        <div className="flex items-start justify-between gap-3 pt-1">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-xl border flex items-center justify-center ${
                isInProgress
                  ? 'bg-amber-500/15 border-amber-500/30'
                  : !isFailed
                  ? 'bg-emerald-500/15 border-emerald-500/30'
                  : 'bg-rose-500/15 border-rose-500/30'
              }`}
            >
              {getHeaderIcon()}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold tracking-wider uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {getCategoryLabel()}
                </span>
                <span
                  className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                    isInProgress
                      ? 'bg-amber-500/20 text-amber-300'
                      : !isFailed
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : 'bg-rose-500/20 text-rose-300'
                  }`}
                >
                  {status}
                </span>
              </div>
              <h4 className="font-bold text-slate-100 text-sm mt-1">
                {title || message || `${appName} execution`}
              </h4>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition"
            title="Dismiss popup"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Detailed Metadata Grid */}
        <div className="mt-3.5 pt-3 border-t border-slate-800/80 space-y-2 text-xs">
          {message && message !== title && (
            <div className="text-slate-300 text-[12px] bg-slate-800/50 p-2 rounded-lg border border-slate-700/50">
              {message}
            </div>
          )}

          <div className="flex items-center justify-between">
            <span className="text-slate-400">Target / Step:</span>
            <span className="font-semibold text-slate-200 font-mono flex items-center gap-1">
              {title?.toLowerCase().includes('search') ? (
                <Search className="w-3.5 h-3.5 text-cyan-400" />
              ) : title?.toLowerCase().includes('message') ? (
                <MessageCircle className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Monitor className="w-3.5 h-3.5 text-cyan-400" />
              )}
              {appName || 'Desktop Operation'}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400">Task Status:</span>
            {getStatusBadge()}
          </div>

          {executionTimeMs !== undefined && (
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Execution Time:</span>
              <span className="font-mono text-cyan-300 flex items-center gap-1">
                <Clock className="w-3 h-3 text-cyan-400" />
                {Math.round(executionTimeMs)}ms
              </span>
            </div>
          )}

          {error && (
            <div className="p-2.5 rounded-lg bg-rose-950/60 border border-rose-800/60 text-[11px] text-rose-300 mt-2">
              <span className="font-semibold">Error:</span> {error}
            </div>
          )}
        </div>

        {/* Action Buttons Row */}
        <div className="mt-4 flex items-center gap-2 pt-2 border-t border-slate-800/80">
          {(rawApp || appName) && !isInProgress && (
            <button
              type="button"
              onClick={handlePopUpDirectly}
              className="flex-1 py-2 px-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-semibold text-xs transition shadow-md flex items-center justify-center gap-1.5 active:scale-95"
              title="Click to pop up the application window directly"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Pop Up {appName}</span>
            </button>
          )}

          {isFailed && onRetry && (
            <button
              type="button"
              onClick={() => onRetry(appName)}
              className="py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs transition border border-slate-700 flex items-center justify-center gap-1"
            >
              <RotateCw className="w-3 h-3 text-cyan-400" />
              <span>Retry</span>
            </button>
          )}

          <button
            type="button"
            onClick={onClose}
            className="py-2 px-3 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 text-slate-400 hover:text-slate-200 text-xs transition border border-slate-700/60 ml-auto"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
