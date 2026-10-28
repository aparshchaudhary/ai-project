import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, CheckCircle, XCircle, Clock, Zap } from 'lucide-react';
import { api } from '../services/api';
import { AnalyticsData } from '../types';

export const AnalyticsPage: React.FC = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);

  useEffect(() => {
    api.getAnalytics().then(setData).catch(console.error);
  }, []);

  if (!data) {
    return <div className="p-12 text-center text-slate-400">Loading analytics...</div>;
  }

  const maxTimelineCount = Math.max(...data.commands_timeline.map((d) => d.count), 1);
  const maxIntentCount = Math.max(...data.most_used_intents.map((d) => d.count), 1);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl md:text-2xl font-bold text-white flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-blue-400" />
          Analytics & Usage Telemetry
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Performance metrics, success rate breakdowns, and frequency patterns.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Total Commands */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Total Commands</span>
            <Zap className="w-4 h-4 text-blue-400" />
          </div>
          <p className="text-2xl font-extrabold text-white">{data.total_commands}</p>
          <span className="text-[11px] text-blue-400 font-medium">All logged executions</span>
        </div>

        {/* Success Rate */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Success Rate</span>
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-extrabold text-emerald-400">{data.success_rate_percent}%</p>
          <span className="text-[11px] text-slate-400 font-medium">{data.successful_commands} successful</span>
        </div>

        {/* Average Latency */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Avg Latency</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-extrabold text-white">{data.average_response_time_ms} ms</p>
          <span className="text-[11px] text-amber-400 font-medium">End-to-end response time</span>
        </div>

        {/* Commands Today */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Today's Actions</span>
            <TrendingUp className="w-4 h-4 text-purple-400" />
          </div>
          <p className="text-2xl font-extrabold text-purple-400">{data.commands_today}</p>
          <span className="text-[11px] text-slate-400 font-medium">Recorded since midnight</span>
        </div>
      </div>

      {/* Visual Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Timeline Chart */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center justify-between">
            <span>Daily Command Volume (Last 7 Days)</span>
          </h3>

          <div className="h-48 flex items-end justify-between gap-2 pt-6 pb-2 border-b border-slate-800">
            {data.commands_timeline.map((item, idx) => {
              const heightPct = Math.round((item.count / maxTimelineCount) * 100);
              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
                  <span className="text-[10px] text-slate-400 opacity-0 group-hover:opacity-100 transition font-mono">
                    {item.count}
                  </span>
                  <div
                    className="w-full max-w-[28px] rounded-t-lg bg-gradient-to-t from-blue-600 to-cyan-400 group-hover:from-blue-500 group-hover:to-cyan-300 transition-all shadow-md"
                    style={{ height: `${Math.max(8, heightPct)}%` }}
                  />
                  <span className="text-[10px] font-mono text-slate-400">{item.date}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Most-Used Intents Bar Chart */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold text-white">
            Most Frequently Invoked Intents
          </h3>

          <div className="space-y-2.5">
            {data.most_used_intents.length === 0 ? (
              <p className="text-xs text-slate-500">No intent metrics yet.</p>
            ) : (
              data.most_used_intents.map((item, idx) => {
                const widthPct = Math.round((item.count / maxIntentCount) * 100);
                return (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-mono text-slate-300">{item.intent}</span>
                      <span className="font-bold text-white">{item.count}</span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-indigo-500 to-blue-500 h-full rounded-full transition-all"
                        style={{ width: `${widthPct}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
