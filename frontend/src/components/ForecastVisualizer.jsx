import React, { useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from 'recharts';
import { Wind, Sun, AlertTriangle, BatteryCharging, ShieldAlert, Cpu, CheckCircle2, ChevronRight } from 'lucide-react';

export default function ForecastVisualizer({ forecastData, horizon, onSelectHorizon, isLoading }) {
  const [activeFilter, setActiveFilter] = useState('ALL'); // 'ALL', 'OVER_CAPACITY', 'UNDER_CAPACITY', 'MAINTENANCE'

  if (isLoading) {
    return (
      <div className="bg-[#101726] border border-slate-800 rounded-xl p-8 flex items-center justify-center min-h-[440px]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs text-slate-400 font-medium">
            Generating {horizon} physics-informed quantile forecasts and power management alerts...
          </span>
        </div>
      </div>
    );
  }

  if (!forecastData || !forecastData.data) {
    return (
      <div className="bg-[#101726] border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-sm">
        No forecast data available for this fleet.
      </div>
    );
  }

  const { site_name, capacity_mw, site_type, summary, data, mitigations } = forecastData;
  const isWind = site_type === 'wind' || forecastData.site_id?.includes('wind');

  // Format chart data with statistical flags
  const chartData = data.map((pt, idx) => {
    const timeLabel = pt.time.length >= 16 ? pt.time.substring(11, 16) : `T+${idx}h`;
    return {
      time: timeLabel,
      fullTime: pt.time,
      p10: pt.p10_mw,
      p50: pt.p50_mw,
      p90: pt.p90_mw,
      actual: pt.actual_mw !== null && pt.actual_mw !== undefined ? pt.actual_mw : null,
      physics: pt.physics_potential_mw,
      statusFlag: pt.status_flag,
      flagReason: pt.flag_reason,
      mitigationAction: pt.mitigation_action
    };
  });

  return (
    <div className="bg-[#101726] border border-slate-800 rounded-xl p-5 shadow-sm space-y-5">
      
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <div className={`p-2 rounded-lg ${isWind ? 'bg-cyan-500/15 text-cyan-400' : 'bg-amber-500/15 text-amber-400'}`}>
              {isWind ? <Wind className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-tight">{site_name}</h2>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-semibold">
                  {capacity_mw} MW Nominal
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {isWind ? 'windpowerlib Aerodynamics Engine' : 'pvlib Irradiance & POA Transposition Engine'} — 15-Min Quantile Intervals
              </p>
            </div>
          </div>
        </div>

        {/* Horizon Toggle */}
        <div className="flex items-center gap-1.5 bg-slate-900/90 border border-slate-800 p-1 rounded-lg self-start md:self-auto">
          {['24h', '48h', '72h'].map((h) => (
            <button
              key={h}
              onClick={() => onSelectHorizon(h)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                horizon === h
                  ? 'bg-emerald-500 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              {h === '24h' ? '24 Hours' : h === '48h' ? '48 Hours (Recommended)' : '72 Hours'}
            </button>
          ))}
        </div>
      </div>

      {/* Statistical Risk Indicators Banner */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Over-Capacity / Curtailment Risk */}
          <div className={`p-3 rounded-lg border flex items-center gap-3 ${
            summary.over_capacity_intervals > 0
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
              : 'bg-slate-900/50 border-slate-800 text-slate-400'
          }`}>
            <AlertTriangle className={`h-5 w-5 ${summary.over_capacity_intervals > 0 ? 'text-amber-400' : 'text-slate-500'}`} />
            <div>
              <div className="text-xs font-bold text-white">
                {summary.over_capacity_intervals} Over-Capacity Intervals ({summary.estimated_curtailment_mwh} MWh)
              </div>
              <div className="text-[11px] text-slate-400">
                P50 &gt; 82% capacity — BESS charging / curtailment risk
              </div>
            </div>
          </div>

          {/* Under-Capacity / Deficit Risk */}
          <div className={`p-3 rounded-lg border flex items-center gap-3 ${
            summary.under_capacity_intervals > 0
              ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
              : 'bg-slate-900/50 border-slate-800 text-slate-400'
          }`}>
            <BatteryCharging className={`h-5 w-5 ${summary.under_capacity_intervals > 0 ? 'text-rose-400' : 'text-slate-500'}`} />
            <div>
              <div className="text-xs font-bold text-white">
                {summary.under_capacity_intervals} Under-Capacity Intervals ({summary.estimated_deficit_mwh} MWh)
              </div>
              <div className="text-[11px] text-slate-400">
                P50 &lt; 12% firm capacity — Peaker / BESS discharge needed
              </div>
            </div>
          </div>

          {/* Predictive Maintenance Anomaly */}
          <div className={`p-3 rounded-lg border flex items-center gap-3 ${
            summary.maintenance_anomaly_intervals > 0
              ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300'
              : 'bg-slate-900/50 border-slate-800 text-slate-400'
          }`}>
            <ShieldAlert className={`h-5 w-5 ${summary.maintenance_anomaly_intervals > 0 ? 'text-cyan-400' : 'text-slate-500'}`} />
            <div>
              <div className="text-xs font-bold text-white">
                {summary.maintenance_anomaly_intervals} Degradation Anomalies
              </div>
              <div className="text-[11px] text-slate-400">
                Actual vs Physics PR &lt; 68% — Soiling/Inverter/Yaw check
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Forecast Chart */}
      <div className="h-[380px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="p90Band" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#1f293d' }}
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#1f293d' }}
              tickFormatter={(v) => `${Math.round(v)} MW`}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  const pt = payload[0].payload;
                  return (
                    <div className="bg-slate-900 border border-slate-700/80 rounded-lg p-3.5 shadow-xl text-xs space-y-1.5 max-w-xs">
                      <div className="font-semibold text-white border-b border-slate-800 pb-1 flex justify-between gap-4">
                        <span>{pt.fullTime ? pt.fullTime.replace('T', ' ') : label}</span>
                        <span className="text-slate-400 uppercase">{site_type}</span>
                      </div>
                      
                      {pt.actual !== null && (
                        <div className="flex justify-between gap-4 text-sky-400 font-semibold">
                          <span>Observed Generation:</span>
                          <span>{pt.actual.toFixed(1)} MW</span>
                        </div>
                      )}
                      
                      <div className="flex justify-between gap-4 text-emerald-400 font-semibold">
                        <span>P50 Expected Forecast:</span>
                        <span>{pt.p50.toFixed(1)} MW</span>
                      </div>

                      <div className="flex justify-between gap-4 text-amber-300 font-medium">
                        <span>Physics Potential:</span>
                        <span>{pt.physics ? `${pt.physics.toFixed(1)} MW` : 'N/A'}</span>
                      </div>

                      <div className="flex justify-between gap-4 text-slate-400">
                        <span>Quantile Spread (P10 - P90):</span>
                        <span className="text-slate-200">{pt.p10.toFixed(1)} — {pt.p90.toFixed(1)} MW</span>
                      </div>

                      {pt.statusFlag !== 'NORMAL' && (
                        <div className="pt-2 border-t border-slate-800 space-y-1">
                          <div className={`font-bold text-[11px] ${
                            pt.statusFlag === 'OVER_CAPACITY_RISK' ? 'text-amber-400' :
                            pt.statusFlag === 'UNDER_CAPACITY_RISK' ? 'text-rose-400' : 'text-cyan-400'
                          }`}>
                            ⚠️ {pt.statusFlag.replace(/_/g, ' ')}
                          </div>
                          {pt.mitigationAction && (
                            <div className="text-[10px] text-slate-300 bg-slate-800/80 p-1.5 rounded">
                              <span className="font-semibold text-emerald-400">Action:</span> {pt.mitigationAction}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend
              verticalAlign="top"
              align="right"
              iconType="circle"
              wrapperStyle={{ paddingBottom: '10px', fontSize: '11px', color: '#94a3b8' }}
            />

            {/* P90 Area */}
            <Area
              type="monotone"
              dataKey="p90"
              name="P90 Upper Bound"
              stroke="#10b981"
              strokeDasharray="4 4"
              strokeWidth={1}
              fill="url(#p90Band)"
            />

            {/* P10 Line */}
            <Line
              type="monotone"
              dataKey="p10"
              name="P10 Lower Bound"
              stroke="#059669"
              strokeDasharray="3 3"
              strokeWidth={1}
              dot={false}
            />

            {/* Physics Potential Line */}
            <Line
              type="monotone"
              dataKey="physics"
              name={isWind ? "windpowerlib Potential" : "pvlib POA Potential"}
              stroke="#f59e0b"
              strokeWidth={1.5}
              strokeDasharray="2 2"
              dot={false}
            />

            {/* P50 Median Point Forecast */}
            <Line
              type="monotone"
              dataKey="p50"
              name="P50 Expected Forecast"
              stroke="#10b981"
              strokeWidth={2.5}
              dot={false}
            />

            {/* Actuals (where present) */}
            <Line
              type="monotone"
              dataKey="actual"
              name="Observed Generation"
              stroke="#38bdf8"
              strokeWidth={2}
              dot={{ r: 2.5, fill: '#38bdf8' }}
              connectNulls={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Actionable Mitigation Recommendations Drawer */}
      {mitigations && mitigations.length > 0 && (
        <div className="pt-3 border-t border-slate-800 space-y-2.5">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>Statistical Power Management & Mitigation Recommendations</span>
            </h3>
            <span className="text-[11px] text-slate-400">{mitigations.length} Flagged Actions</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {mitigations.slice(0, 4).map((mit) => (
              <div
                key={mit.id}
                className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 flex items-start gap-2.5 hover:border-slate-700 transition-colors"
              >
                <div className={`p-1.5 rounded-md mt-0.5 ${
                  mit.severity === 'HIGH' ? 'bg-rose-500/15 text-rose-400' :
                  mit.severity === 'WARNING' ? 'bg-amber-500/15 text-amber-400' : 'bg-cyan-500/15 text-cyan-400'
                }`}>
                  <AlertTriangle className="h-3.5 w-3.5" />
                </div>
                <div className="flex-1 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">{mit.title}</span>
                    <span className="text-[10px] font-mono text-slate-400">{mit.time?.substring(11, 16)}</span>
                  </div>
                  <p className="text-slate-400 text-[11px] mt-0.5 leading-snug">{mit.description}</p>
                  <div className="mt-1.5 p-1.5 rounded bg-slate-800/80 text-[11px] text-emerald-300 font-medium">
                    ⚡ {mit.action}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary KPI Footer */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-800/80">
          <div className="bg-slate-900/60 rounded-lg p-2.5 border border-slate-800">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Peak Generation</span>
            <div className="text-sm font-bold text-white mt-0.5">
              {summary.peak_generation_mw} MW
            </div>
          </div>
          <div className="bg-slate-900/60 rounded-lg p-2.5 border border-slate-800">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Expected Generation</span>
            <div className="text-sm font-bold text-emerald-400 mt-0.5">
              {summary.total_expected_energy_mwh.toLocaleString()} MWh
            </div>
          </div>
          <div className="bg-slate-900/60 rounded-lg p-2.5 border border-slate-800">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Average Capacity Factor</span>
            <div className="text-sm font-bold text-cyan-400 mt-0.5">
              {summary.capacity_factor_pct}%
            </div>
          </div>
          <div className="bg-slate-900/60 rounded-lg p-2.5 border border-slate-800">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Asset Health Score</span>
            <div className="text-sm font-bold text-amber-400 mt-0.5">
              {summary.health_score_pct}%
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
