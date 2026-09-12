import React from 'react';
import { AlertTriangle, CheckCircle, Info, ShieldAlert, ZapOff, Sparkles } from 'lucide-react';

export default function FaultAlertsTable({ alerts }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="bg-[#101726] border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-sm">
        <CheckCircle className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
        All generation assets operating within normal physical parameters. No active faults.
      </div>
    );
  }

  return (
    <div className="bg-[#101726] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400">
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Asset Health & Fault Detection Monitor
            </h2>
            <p className="text-xs text-slate-400">
              Clear-sky divergence, aerodynamic wind ramp tracking, and inverter clipping diagnostics
            </p>
          </div>
        </div>
        <span className="text-xs px-2.5 py-1 bg-rose-500/10 border border-rose-500/30 text-rose-400 font-semibold rounded-full">
          {alerts.length} Active Events
        </span>
      </div>

      {/* Alerts List */}
      <div className="space-y-3">
        {alerts.map((alert) => {
          const isCritical = alert.severity === 'CRITICAL';
          const isWarning = alert.severity === 'WARNING';

          return (
            <div
              key={alert.id}
              className={`p-4 rounded-xl border transition-colors ${
                isCritical
                  ? 'bg-rose-950/20 border-rose-800/60'
                  : isWarning
                  ? 'bg-amber-950/20 border-amber-800/60'
                  : 'bg-slate-900/60 border-slate-800'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider rounded ${
                      isCritical
                        ? 'bg-rose-500 text-white'
                        : isWarning
                        ? 'bg-amber-500 text-slate-950'
                        : 'bg-cyan-500/20 text-cyan-400'
                    }`}
                  >
                    {alert.severity}
                  </span>
                  <span className="text-xs font-bold text-white">{alert.site_name}</span>
                  <span className="text-[10px] px-2 py-0.5 bg-slate-800 rounded text-slate-300 font-mono">
                    {alert.alert_type}
                  </span>
                </div>
                <span className="text-[11px] text-slate-400">
                  {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} UTC
                </span>
              </div>

              <h4 className="text-xs font-semibold text-slate-200 mb-1">{alert.message}</h4>
              {alert.diagnostic_details && (
                <p className="text-[11px] text-slate-400 leading-relaxed bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60">
                  <span className="text-slate-300 font-medium">Diagnostic: </span>
                  {alert.diagnostic_details}
                </p>
              )}
            </div>
          );
        })}
      </div>

    </div>
  );
}
