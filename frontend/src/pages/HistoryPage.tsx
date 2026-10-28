import React, { useState, useEffect } from 'react';
import { History, Search, Trash2, CheckCircle2, XCircle, Clock, ShieldAlert } from 'lucide-react';
import { api } from '../services/api';
import { HistoryItem } from '../types';

export const HistoryPage: React.FC = () => {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const items = await api.getHistory(100, search || undefined, statusFilter || undefined);
      setHistory(items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [search, statusFilter]);

  const handleClearAll = async () => {
    if (window.confirm('Are you sure you want to clear your entire command history?')) {
      await api.clearHistory();
      fetchHistory();
    }
  };

  const handleDeleteItem = async (id: number) => {
    await api.deleteHistoryItem(id);
    setHistory((prev) => prev.filter((i) => i.id !== id));
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-white flex items-center gap-2">
            <History className="w-6 h-6 text-blue-400" />
            Command Audit History
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Audit log of all spoken and executed commands, latency, and security statuses.
          </p>
        </div>

        {history.length > 0 && (
          <button
            onClick={handleClearAll}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600/20 text-red-300 border border-red-500/30 hover:bg-red-600/30 text-xs font-semibold transition"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear All History
          </button>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search commands (e.g. 'Chrome', 'Screenshot', 'Reminder')..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full sm:w-auto"
        >
          <option value="">All Statuses</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
          <option value="pending_confirmation">Pending</option>
          <option value="denied">Denied</option>
        </select>
      </div>

      {/* Table List */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center text-slate-400">Loading history...</div>
        ) : history.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            No history entries matching your query.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/60 uppercase font-semibold text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-5 py-3.5">Command</th>
                  <th className="px-4 py-3.5">Intent</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5">Risk</th>
                  <th className="px-4 py-3.5">Latency</th>
                  <th className="px-4 py-3.5">Time</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {history.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-5 py-3.5 font-medium text-white max-w-xs truncate">
                      "{item.command_text}"
                    </td>
                    <td className="px-4 py-3.5 font-mono text-blue-400">
                      {item.recognized_intent}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-bold uppercase text-[10px] ${item.status === 'success' ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' : (item.status === 'failed' ? 'bg-red-500/10 text-red-300 border border-red-500/20' : 'bg-amber-500/10 text-amber-300 border border-amber-500/20')}`}>
                        {item.status === 'success' ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                        {item.status}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${item.risk_level === 'high' ? 'bg-red-500/20 text-red-400' : (item.risk_level === 'medium' ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-800 text-slate-400')}`}>
                        {item.risk_level}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-slate-400">
                      {item.execution_time_ms.toFixed(0)} ms
                    </td>
                    <td className="px-4 py-3.5 text-slate-400">
                      {new Date(item.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <button
                        onClick={() => handleDeleteItem(item.id)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-slate-800 transition"
                        title="Delete log"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
