import React, { useEffect, useState } from 'react';
import { Smartphone, Laptop, Wifi, WifiOff, Battery, BatteryCharging, HardDrive, Cpu, RefreshCw, ShieldCheck } from 'lucide-react';
import { ConnectedDevice } from '../types';

interface ConnectedDevicesPanelProps {
  className?: string;
}

export const ConnectedDevicesPanel: React.FC<ConnectedDevicesPanelProps> = ({ className = '' }) => {
  const [devices, setDevices] = useState<ConnectedDevice[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchDevices = async () => {
    try {
      const res = await fetch('/api/devices');
      if (res.ok) {
        const data = await res.json();
        setDevices(data.devices || []);
      }
    } catch (e) {
      console.debug('Failed to fetch devices:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-md ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-gradient-to-tr from-sky-500/20 to-indigo-500/20 border border-sky-500/30">
            <Smartphone className="w-5 h-5 text-sky-400" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-100 text-base flex items-center gap-2">
              Connected Devices
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-sky-400 font-normal">
                Cross-Platform Agent Mesh
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Coordinated execution across Android & Windows nodes
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={fetchDevices}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          title="Refresh device statuses"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Device Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {devices.map((dev) => {
          const isOnline = dev.status === 'online';
          const isAndroid = dev.device_type === 'android';

          return (
            <div
              key={dev.device_id}
              className={`p-4 rounded-xl border transition flex flex-col justify-between ${
                isOnline
                  ? 'bg-slate-950/70 border-slate-700/60 shadow-lg'
                  : 'bg-slate-950/30 border-slate-800/40 opacity-70'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <div className={`p-2 rounded-lg ${isAndroid ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'}`}>
                      {isAndroid ? <Smartphone className="w-4 h-4" /> : <Laptop className="w-4 h-4" />}
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-slate-100">{dev.device_name}</h4>
                      <span className="text-[11px] font-mono text-slate-400 uppercase">{dev.device_type}</span>
                    </div>
                  </div>

                  {/* Status Badge */}
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${
                    isOnline
                      ? 'bg-emerald-950/80 border border-emerald-500/40 text-emerald-300'
                      : 'bg-slate-800 border border-slate-700 text-slate-400'
                  }`}>
                    {isOnline ? <Wifi className="w-3 h-3 text-emerald-400" /> : <WifiOff className="w-3 h-3 text-slate-400" />}
                    <span>{isOnline ? 'ONLINE' : 'OFFLINE'}</span>
                  </span>
                </div>

                {/* Telemetry row */}
                <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-800/80 text-[11px] text-slate-300">
                  <div className="flex items-center gap-1.5">
                    {dev.is_charging ? (
                      <BatteryCharging className="w-3.5 h-3.5 text-amber-400" />
                    ) : (
                      <Battery className="w-3.5 h-3.5 text-slate-400" />
                    )}
                    <span>{dev.battery_pct !== null && dev.battery_pct !== undefined ? `${dev.battery_pct}%` : 'AC Power'}</span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{dev.ram_usage_pct ? `${dev.ram_usage_pct}% RAM` : 'Active'}</span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <HardDrive className="w-3.5 h-3.5 text-sky-400" />
                    <span>{dev.storage_free_gb ? `${dev.storage_free_gb}GB Free` : 'Ready'}</span>
                  </div>
                </div>
              </div>

              {/* Capabilities Pill Strip */}
              <div className="mt-3 flex flex-wrap gap-1">
                {dev.capabilities && dev.capabilities.slice(0, 4).map((cap, i) => (
                  <span
                    key={i}
                    className="text-[10px] bg-slate-900 text-slate-300 border border-slate-800 px-2 py-0.5 rounded"
                  >
                    {cap.split('.').pop()}
                  </span>
                ))}
                {dev.capabilities && dev.capabilities.length > 4 && (
                  <span className="text-[10px] text-slate-500 self-center">
                    +{dev.capabilities.length - 4} more
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
