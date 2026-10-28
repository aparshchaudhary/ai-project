import React, { useState, useEffect } from 'react';
import { Grid, Plus, Play, Trash2, CheckCircle2, AlertCircle, ExternalLink } from 'lucide-react';
import { api } from '../services/api';
import { AppRegistryItem } from '../types';

export const ApplicationsPage: React.FC = () => {
  const [apps, setApps] = useState<AppRegistryItem[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [appKey, setAppKey] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [execPath, setExecPath] = useState('');
  const [aliases, setAliases] = useState('');
  const [launchMessage, setLaunchMessage] = useState<string | null>(null);

  const fetchApps = async () => {
    try {
      const data = await api.getApplications();
      setApps(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchApps();
  }, []);

  const handleLaunch = async (appKey: string) => {
    try {
      const res = await api.launchApplication(appKey);
      setLaunchMessage(res.message);
      setTimeout(() => setLaunchMessage(null), 4000);
    } catch (e) {
      setLaunchMessage(`Failed to launch: ${e}`);
      setTimeout(() => setLaunchMessage(null), 4000);
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!appKey.trim() || !displayName.trim() || !execPath.trim()) return;

    try {
      const aliasList = aliases
        .split(',')
        .map((s) => s.trim().toLowerCase())
        .filter(Boolean);

      await api.addApplication(appKey.trim().toLowerCase(), displayName.trim(), aliasList, execPath.trim());
      setAppKey('');
      setDisplayName('');
      setExecPath('');
      setAliases('');
      setShowAddModal(false);
      fetchApps();
    } catch (e) {
      alert('Failed to register application.');
    }
  };

  const handleDelete = async (id: number) => {
    await api.deleteApplication(id);
    setApps((prev) => prev.filter((a) => a.id !== id));
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-white flex items-center gap-2">
            <Grid className="w-6 h-6 text-blue-400" />
            Configurable Application Registry
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Registered computer programs available for voice activation (e.g. "Open Chrome", "Launch VS Code").
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/30 transition active:scale-95"
        >
          <Plus className="w-4 h-4" />
          Add Custom App
        </button>
      </div>

      {launchMessage && (
        <div className="p-3.5 rounded-xl bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs font-medium animate-fadeIn">
          {launchMessage}
        </div>
      )}

      {/* Grid of Apps */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {apps.map((app) => (
          <div
            key={app.id}
            className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 space-y-3 transition group relative"
          >
            <div className="flex items-start justify-between">
              <div>
                <h4 className="font-bold text-white text-base">
                  {app.display_name}
                </h4>
                <p className="text-xs font-mono text-blue-400">
                  Voice Key: "{app.app_key}"
                </p>
              </div>

              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold flex items-center gap-1 ${app.is_available ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' : 'bg-slate-800 text-slate-500'}`}>
                {app.is_available ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                {app.is_available ? 'Detected' : 'Custom'}
              </span>
            </div>

            <div className="space-y-1 text-xs text-slate-400">
              <p className="truncate font-mono text-[11px] bg-slate-950 p-1.5 rounded-lg border border-slate-800/80">
                {app.exec_path}
              </p>
              {app.aliases.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {app.aliases.map((al, idx) => (
                    <span key={idx} className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">
                      "{al}"
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <button
                onClick={() => handleLaunch(app.app_key)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600/20 text-blue-300 hover:bg-blue-600 text-xs font-medium hover:text-white transition"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                Launch Now
              </button>

              {app.is_custom && (
                <button
                  onClick={() => handleDelete(app.id)}
                  className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 transition"
                  title="Remove Custom App"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Add Custom App Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 text-white space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Plus className="w-5 h-5 text-blue-400" />
              Register Custom Application
            </h3>

            <form onSubmit={handleAdd} className="space-y-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Application Key (Voice identifier)</label>
                <input
                  type="text"
                  required
                  value={appKey}
                  onChange={(e) => setAppKey(e.target.value)}
                  placeholder="e.g. blender"
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Display Name</label>
                <input
                  type="text"
                  required
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="e.g. Blender 3D"
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Executable Path or Command</label>
                <input
                  type="text"
                  required
                  value={execPath}
                  onChange={(e) => setExecPath(e.target.value)}
                  placeholder="e.g. C:\Program Files\Blender Foundation\blender.exe"
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Voice Aliases (Comma separated)</label>
                <input
                  type="text"
                  value={aliases}
                  onChange={(e) => setAliases(e.target.value)}
                  placeholder="e.g. blender 3d, 3d software, blender"
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white"
                >
                  Save Application
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
