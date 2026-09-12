import React from 'react';
import { Wind, Sun, Activity, Zap, RefreshCw, Layers } from 'lucide-react';

export default function Navbar({ sites, selectedSiteId, onSelectSite, onRefresh, isRefreshing }) {
  const currentSite = sites.find(s => s.id === selectedSiteId) || sites[0];

  return (
    <header className="border-b border-slate-800/80 bg-[#0c111e]/90 backdrop-blur sticky top-0 z-40 px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand & Logo */}
        <div className="flex items-center gap-3.5">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-400 p-0.5 shadow-lg shadow-emerald-500/20">
            <div className="h-full w-full bg-[#090d16] rounded-[10px] flex items-center justify-center">
              <Zap className="h-5 w-5 text-emerald-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-xl tracking-tight text-white">SIROCCO</span>
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-full">
                AI Grid Platform
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium">Renewable Generation Forecasting & Asset Intelligence</p>
          </div>
        </div>

        {/* Global Controls & Site Selector */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
          
          {/* Live Runtime Status */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="font-medium text-slate-300">Models Online (P10/P50/P90)</span>
          </div>

          {/* Site Selector Dropdown */}
          <div className="relative flex items-center">
            <Layers className="absolute left-3 h-4 w-4 text-slate-400 pointer-events-none" />
            <select
              value={selectedSiteId}
              onChange={(e) => onSelectSite(e.target.value)}
              className="pl-9 pr-8 py-2 bg-slate-900 border border-slate-700/80 hover:border-slate-600 rounded-lg text-xs font-semibold text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 appearance-none cursor-pointer transition-all"
            >
              {sites.map((site) => (
                <option key={site.id} value={site.id} className="bg-slate-900 text-slate-200">
                  {site.name} ({site.capacity_mw >= 1 ? `${site.capacity_mw} MW` : `${(site.capacity_mw * 1000).toFixed(1)} kW`})
                </option>
              ))}
            </select>
          </div>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white rounded-lg transition-colors flex items-center justify-center disabled:opacity-50"
            title="Refresh Live Data"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>

      </div>
    </header>
  );
}
