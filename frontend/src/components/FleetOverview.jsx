import React from 'react';
import { Wind, Sun, ShieldCheck, TrendingUp, Cpu, Zap, AlertTriangle } from 'lucide-react';

export default function FleetOverview({ overview, selectedSiteId, onSelectSite }) {
  if (!overview) return null;

  return (
    <div className="space-y-6">
      
      {/* Top 5 KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        
        {/* Total Fleet Capacity */}
        <div className="bg-[#101726] border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-sm hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Grid Capacity</span>
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Zap className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white tracking-tight">
              {overview.total_capacity_mw} <span className="text-xs font-medium text-slate-400">MW</span>
            </div>
            <div className="text-[11px] text-emerald-400 mt-1 font-medium flex items-center gap-1">
              <span>2 Unified Fleets (Solar + Wind)</span>
            </div>
          </div>
        </div>

        {/* Live Generation Output */}
        <div className="bg-[#101726] border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-sm hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Live Fleet Output</span>
            <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white tracking-tight">
              {overview.current_generation_mw} <span className="text-xs font-medium text-slate-400">MW</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1 font-medium">
              Capacity Factor: <span className="text-cyan-400 font-semibold">{overview.capacity_factor_pct}%</span>
            </div>
          </div>
        </div>

        {/* 48h Peak Forecast */}
        <div className="bg-[#101726] border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-sm hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">48h Peak Projection</span>
            <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400">
              <Cpu className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white tracking-tight">
              {overview.forecast_24h_peak_mw} <span className="text-xs font-medium text-slate-400">MW</span>
            </div>
            <div className="text-[11px] text-amber-400 mt-1 font-medium">
              P50 Median Grid Supply
            </div>
          </div>
        </div>

        {/* Active Grid Alerts */}
        <div className="bg-[#101726] border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-sm hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Grid Alerts</span>
            <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400">
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white tracking-tight">
              {overview.active_alerts_count} <span className="text-xs font-medium text-slate-400">Active</span>
            </div>
            <div className="text-[11px] text-rose-400 mt-1 font-medium">
              Real-Time Fault Monitored
            </div>
          </div>
        </div>

        {/* Fleet Health Score */}
        <div className="bg-[#101726] border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-sm hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Fleet Health Index</span>
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
              <ShieldCheck className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white tracking-tight">
              {overview.fleet_health_score}%
            </div>
            <div className="text-[11px] text-emerald-400 mt-1 font-medium">
              Physics PR Benchmark
            </div>
          </div>
        </div>

      </div>

      {/* Unified Fleet Entities Selection Cards */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
            <span>Integrated Generation Fleets</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-normal">
              2 Unified Entities
            </span>
          </h2>
          <span className="text-xs text-slate-400">Select fleet to view 48h-72h forecast, risk flags & physics attributions</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {overview.sites.map((site) => {
            const isSelected = site.id === selectedSiteId;
            const isWind = site.type === 'wind' || site.id.includes('wind');
            return (
              <div
                key={site.id}
                onClick={() => onSelectSite(site.id)}
                className={`p-5 rounded-xl cursor-pointer border transition-all ${
                  isSelected
                    ? 'bg-slate-900 border-emerald-500 shadow-lg shadow-emerald-500/10 ring-2 ring-emerald-500/40'
                    : 'bg-[#101726] border-slate-800 hover:border-slate-700 hover:bg-slate-900/60'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl ${isWind ? 'bg-cyan-500/15 text-cyan-400' : 'bg-amber-500/15 text-amber-400'}`}>
                      {isWind ? <Wind className="h-6 w-6" /> : <Sun className="h-6 w-6" />}
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white">{site.name}</h3>
                      <p className="text-xs text-slate-400">
                        {isWind
                          ? '6 Combined Wind Farms | windpowerlib Aerodynamics'
                          : '8 Combined Solar Plants | pvlib POA Irradiance Physics'}
                      </p>
                    </div>
                  </div>
                  <span className={`px-2.5 py-1 text-xs font-bold rounded-full border ${
                    isSelected
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                      : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}>
                    {isSelected ? 'Active Selection' : 'Click to View'}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3 pt-3 border-t border-slate-800/80 text-xs">
                  <div>
                    <span className="text-slate-400 block text-[11px]">Fleet Capacity:</span>
                    <span className="font-bold text-white text-sm">{site.capacity_mw} MW</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px]">Live Generation:</span>
                    <span className="font-bold text-emerald-400 text-sm">{site.current_generation_mw} MW</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px]">Health Performance:</span>
                    <span className="font-bold text-cyan-400 text-sm">{site.health_score}%</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
