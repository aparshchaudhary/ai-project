import React, { useState, useEffect } from 'react';
import {
  Shield,
  Lock,
  FolderLock,
  Plus,
  Trash2,
  RefreshCw,
  Clock,
  Eye,
  CheckCircle,
  AlertTriangle,
  FolderPlus,
  FileCheck,
} from 'lucide-react';
import { api } from '../services/api';
import { SecurityPermissionsData, AuditLogEntry } from '../types';

export const PermissionsPage: React.FC = () => {
  const [permData, setPermData] = useState<SecurityPermissionsData | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);

  // New Grant Form
  const [newScope, setNewScope] = useState('app_launch');
  const [newTarget, setNewTarget] = useState('whatsapp');
  const [newDays, setNewDays] = useState(30);

  // New Directory Form
  const [newDir, setNewDir] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [pRes, aRes] = await Promise.all([
        api.getSecurityPermissions(),
        api.getAuditLogs(30),
      ]);
      setPermData(pRes);
      setAuditLogs(aRes.logs);
    } catch (e) {
      console.error('Failed to load permissions data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleGrant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTarget.trim()) return;
    try {
      await api.grantPermission(newScope, newTarget.trim(), newDays);
      setNewTarget('');
      loadData();
    } catch (e) {
      alert('Failed to grant permission');
    }
  };

  const handleRevoke = async (scope: string, target: string) => {
    if (!confirm(`Revoke persistent permission for '${scope}:${target}'?`)) return;
    try {
      await api.revokePermission(scope, target);
      loadData();
    } catch (e) {
      alert('Failed to revoke permission');
    }
  };

  const handleAddDir = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDir.trim()) return;
    try {
      await api.addAuthorizedDirectory(newDir.trim());
      setNewDir('');
      loadData();
    } catch (e: any) {
      alert(e.message || 'Failed to add directory');
    }
  };

  const handleRemoveDir = async (dir: string) => {
    if (!confirm(`Remove directory '${dir}' from sandbox allowlist?`)) return;
    try {
      await api.removeAuthorizedDirectory(dir);
      loadData();
    } catch (e) {
      alert('Failed to remove directory');
    }
  };

  const perms = permData?.persistent_permissions || {};
  const permKeys = Object.keys(perms);

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/20">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Security, Privacy & Sandboxed Permissions
            </h1>
            <p className="text-sm text-slate-400">
              Persistent authorization registry preventing repeated nagging prompts, Windows DPAPI vault, and bounded file allowlists.
            </p>
          </div>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium text-sm border border-slate-700 transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* DPAPI Security Boundary Banner */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-blue-950/60 to-indigo-950/60 border border-blue-800/40 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Lock className="w-5 h-5 text-cyan-400 flex-shrink-0" />
          <div className="text-xs">
            <p className="font-semibold text-slate-200">
              Windows DPAPI Encryption Boundary Active
            </p>
            <p className="text-slate-400">
              User credentials & permissions are encrypted with hardware OS keys and saved in <code className="text-cyan-300 font-mono">%USERPROFILE%\.aura_assistant</code> outside the source repository.
            </p>
          </div>
        </div>

        <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
          <CheckCircle className="w-3.5 h-3.5" /> DPAPI Encrypted
        </span>
      </div>

      {/* Grid: Persistent Permissions & Authorized Folders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Persistent Permissions Card */}
        <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileCheck className="w-5 h-5 text-blue-400" />
              <h2 className="text-base font-semibold text-white">Active Persistent Permissions</h2>
            </div>
            <span className="text-xs font-mono text-cyan-400">
              {permKeys.length} {permKeys.length === 1 ? 'grant' : 'grants'} active
            </span>
          </div>

          <p className="text-xs text-slate-400">
            Approved applications (like WhatsApp or Chrome) are persistently cached here so the assistant executes commands immediately without prompting every time.
          </p>

          {/* Add Permission Form */}
          <form onSubmit={handleGrant} className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
              Grant New Persistent Scope
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <select
                value={newScope}
                onChange={(e) => setNewScope(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none"
              >
                <option value="app_launch">App Launch</option>
                <option value="file_read">File Read</option>
                <option value="file_write">File Write</option>
                <option value="clipboard_access">Clipboard Access</option>
                <option value="screenshot">Screenshot</option>
              </select>

              <input
                type="text"
                placeholder="Target (e.g. whatsapp)"
                value={newTarget}
                onChange={(e) => setNewTarget(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none"
              />

              <div className="flex gap-2">
                <input
                  type="number"
                  placeholder="Days"
                  value={newDays}
                  onChange={(e) => setNewDays(Number(e.target.value))}
                  min={1}
                  max={365}
                  className="w-16 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-200 text-center focus:outline-none"
                />
                <button
                  type="submit"
                  className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition"
                >
                  <Plus className="w-3.5 h-3.5" /> Grant
                </button>
              </div>
            </div>
          </form>

          {/* Permissions List */}
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {permKeys.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-4">
                No custom persistent permissions granted yet. Standard safe apps are authorized automatically on first use.
              </p>
            ) : (
              permKeys.map((key) => {
                const item = perms[key];
                return (
                  <div
                    key={key}
                    className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 flex items-center justify-between gap-3 text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white uppercase text-[11px] px-1.5 py-0.5 rounded bg-blue-900/40 text-blue-300 border border-blue-800/60 font-mono">
                          {item.scope}
                        </span>
                        <span className="font-mono text-cyan-300 font-bold">{item.target}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        Valid for {item.duration_days} days
                      </p>
                    </div>

                    <button
                      onClick={() => handleRevoke(item.scope, item.target)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 transition"
                      title="Revoke permission"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* 2. Bounded Directory Sandbox Card */}
        <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FolderLock className="w-5 h-5 text-indigo-400" />
              <h2 className="text-base font-semibold text-white">Bounded Directory Sandbox</h2>
            </div>
            <span className="text-xs font-mono text-indigo-400">
              {permData?.authorized_directories.length || 0} folders allowed
            </span>
          </div>

          <p className="text-xs text-slate-400">
            File creation, reading, and deletion are strictly bounded to this allowlist. Any directory traversal attempts (e.g. <code className="text-rose-400">../../Windows</code>) are automatically rejected.
          </p>

          {/* Add Directory Form */}
          <form onSubmit={handleAddDir} className="flex gap-2">
            <input
              type="text"
              placeholder="Absolute folder path (e.g. C:\Projects)"
              value={newDir}
              onChange={(e) => setNewDir(e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              type="submit"
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
            >
              <FolderPlus className="w-4 h-4" /> Add
            </button>
          </form>

          {/* Directory List */}
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {permData?.authorized_directories.map((dir, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 flex items-center justify-between gap-3 text-xs"
              >
                <div className="truncate">
                  <span className="font-mono text-slate-300 truncate block" title={dir}>
                    {dir}
                  </span>
                  <span className="text-[10px] text-emerald-400">✓ Protected Sandbox Allowed</span>
                </div>

                {idx > 2 && (
                  <button
                    onClick={() => handleRemoveDir(dir)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 transition flex-shrink-0"
                    title="Remove folder from allowlist"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 3. Security Audit Logs Viewer with Secret Redaction */}
      <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Eye className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-semibold text-white">Security & Permission Audit Logs</h2>
          </div>
          <span className="text-xs text-slate-500">API keys & credentials automatically masked</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Timestamp</th>
                <th className="py-2.5 px-3 font-semibold">Action</th>
                <th className="py-2.5 px-3 font-semibold">Scope</th>
                <th className="py-2.5 px-3 font-semibold">Result</th>
                <th className="py-2.5 px-3 font-semibold">Audit Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-slate-500">
                    No security events logged yet.
                  </td>
                </tr>
              ) : (
                auditLogs.map((log, i) => (
                  <tr key={i} className="hover:bg-slate-800/40 transition">
                    <td className="py-2 px-3 text-slate-400 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="py-2 px-3 font-bold text-slate-200">{log.action}</td>
                    <td className="py-2 px-3 text-cyan-400">{log.scope}</td>
                    <td className="py-2 px-3">
                      {log.success ? (
                        <span className="text-emerald-400 font-bold">ALLOWED</span>
                      ) : (
                        <span className="text-rose-400 font-bold">BLOCKED</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-slate-400 max-w-xs truncate" title={JSON.stringify(log.details)}>
                      {JSON.stringify(log.details)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
