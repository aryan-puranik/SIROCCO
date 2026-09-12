import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from 'recharts';
import { Sliders, RefreshCw, Sun, Wind, Activity, Zap, TrendingUp } from 'lucide-react';
import { runWhatIfSimulation } from '../services/api';

export default function WhatIfSimulator() {
  const [activeDomain, setActiveDomain] = useState('solar'); // 'solar' or 'wind'

  // Solar params
  const [solarParams, setSolarParams] = useState({
    solar_capacity_mw: 545.0,
    panel_tilt_deg: 30.0,
    panel_azimuth_deg: 180.0,
    inverter_capacity_mw: 545.0,
    soiling_loss_pct: 3.0
  });

  // Wind params
  const [windParams, setWindParams] = useState({
    wind_capacity_mw: 596.0,
    hub_height_m: 100.0,
    pitch_offset_deg: 0.0,
    cut_in_speed_ms: 3.0,
    air_density_kg_m3: 1.225,
    derating_pct: 0.0
  });

  const [simResult, setSimResult] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);

  // Trigger simulation on param change
  useEffect(() => {
    let active = true;

    const fetchSim = async () => {
      setIsSimulating(true);
      try {
        const payload = activeDomain === 'solar'
          ? { domain: 'solar', ...solarParams }
          : { domain: 'wind', ...windParams };

        const res = await runWhatIfSimulation(payload);
        if (active) setSimResult(res);
      } catch (err) {
        console.error('Simulation error:', err);
      } finally {
        if (active) setIsSimulating(false);
      }
    };

    const handler = setTimeout(fetchSim, 80);
    return () => {
      active = false;
      clearTimeout(handler);
    };
  }, [activeDomain, solarParams, windParams]);

  const handleResetSolar = () => {
    setSolarParams({
      solar_capacity_mw: 545.0,
      panel_tilt_deg: 30.0,
      panel_azimuth_deg: 180.0,
      inverter_capacity_mw: 545.0,
      soiling_loss_pct: 3.0
    });
  };

  const handleResetWind = () => {
    setWindParams({
      wind_capacity_mw: 596.0,
      hub_height_m: 100.0,
      pitch_offset_deg: 0.0,
      cut_in_speed_ms: 3.0,
      air_density_kg_m3: 1.225,
      derating_pct: 0.0
    });
  };

  const chartData = simResult?.intervals?.map((item) => ({
    time: item.time,
    baseline: item.baseline_mw !== undefined ? item.baseline_mw : (item.baseline_wh ? item.baseline_wh / 1000 : 0),
    simulated: item.simulated_mw !== undefined ? item.simulated_mw : (item.simulated_wh ? item.simulated_wh / 1000 : 0),
    delta: item.delta_mw !== undefined ? item.delta_mw : (item.delta_wh ? item.delta_wh / 1000 : 0)
  })) || [];

  return (
    <div className="bg-[#101726] border border-slate-800 rounded-xl p-5 shadow-sm space-y-6">
      
      {/* Header & Fleet Domain Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Sliders className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">
                Digital Twin "What-If" Physics Simulator
              </h2>
              <p className="text-xs text-slate-400">
                Interactive real-time physics knobs for both Solar and Wind fleets
              </p>
            </div>
          </div>
        </div>

        {/* Fleet Domain Switcher & Reset */}
        <div className="flex items-center gap-3">
          <div className="flex bg-slate-900 border border-slate-800 p-1 rounded-lg">
            <button
              onClick={() => setActiveDomain('solar')}
              className={`px-3 py-1.5 text-xs font-bold rounded-md flex items-center gap-1.5 transition-all ${
                activeDomain === 'solar'
                  ? 'bg-amber-500 text-slate-950 shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Sun className="h-3.5 w-3.5" />
              <span>Solar Fleet (545 MW)</span>
            </button>
            <button
              onClick={() => setActiveDomain('wind')}
              className={`px-3 py-1.5 text-xs font-bold rounded-md flex items-center gap-1.5 transition-all ${
                activeDomain === 'wind'
                  ? 'bg-cyan-500 text-slate-950 shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Wind className="h-3.5 w-3.5" />
              <span>Wind Fleet (596 MW)</span>
            </button>
          </div>

          <button
            onClick={activeDomain === 'solar' ? handleResetSolar : handleResetWind}
            className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-xs font-semibold text-slate-300 hover:text-white transition-colors flex items-center gap-1.5"
            title="Reset to baseline"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Reset</span>
          </button>
        </div>
      </div>

      {/* Domain Controls Grid */}
      {activeDomain === 'solar' ? (
        /* SOLAR KNOBS */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 bg-slate-900/50 p-4 rounded-xl border border-slate-800">
          
          {/* DC Capacity */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300">Installed Solar Capacity</span>
              <span className="font-mono font-bold text-amber-400">{solarParams.solar_capacity_mw} MW</span>
            </div>
            <input
              type="range"
              min="100"
              max="1000"
              step="10"
              value={solarParams.solar_capacity_mw}
              onChange={(e) => setSolarParams({ ...solarParams, solar_capacity_mw: parseFloat(e.target.value) })}
              className="w-full accent-amber-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>100 MW</span>
              <span>545 MW (Base)</span>
              <span>1,000 MW</span>
            </div>
          </div>

          {/* Panel Tilt Angle */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300">Array Tilt Angle</span>
              <span className="font-mono font-bold text-emerald-400">{solarParams.panel_tilt_deg}°</span>
            </div>
            <input
              type="range"
              min="0"
              max="60"
              step="1"
              value={solarParams.panel_tilt_deg}
              onChange={(e) => setSolarParams({ ...solarParams, panel_tilt_deg: parseFloat(e.target.value) })}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0° (Flat)</span>
              <span>30° (Base)</span>
              <span>60° (Steep)</span>
            </div>
          </div>

          {/* Panel Azimuth */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300">Array Azimuth Angle</span>
              <span className="font-mono font-bold text-cyan-400">{solarParams.panel_azimuth_deg}°</span>
            </div>
            <input
              type="range"
              min="90"
              max="270"
              step="5"
              value={solarParams.panel_azimuth_deg}
              onChange={(e) => setSolarParams({ ...solarParams, panel_azimuth_deg: parseFloat(e.target.value) })}
              className="w-full accent-cyan-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>90° (East)</span>
              <span>180° (South Base)</span>
              <span>270° (West)</span>
            </div>
          </div>

          {/* AC Inverter Capacity */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300">Inverter AC Export Limit</span>
              <span className="font-mono font-bold text-indigo-400">{solarParams.inverter_capacity_mw} MW</span>
            </div>
            <input
              type="range"
              min="100"
              max="800"
              step="10"
              value={solarParams.inverter_capacity_mw}
              onChange={(e) => setSolarParams({ ...solarParams, inverter_capacity_mw: parseFloat(e.target.value) })}
              className="w-full accent-indigo-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>100 MW</span>
              <span>545 MW (Base)</span>
              <span>800 MW</span>
            </div>
          </div>

          {/* Soiling Loss */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300">Dust & Soiling Factor</span>
              <span className="font-mono font-bold text-rose-400">{solarParams.soiling_loss_pct}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="15"
              step="0.5"
              value={solarParams.soiling_loss_pct}
              onChange={(e) => setSolarParams({ ...solarParams, soiling_loss_pct: parseFloat(e.target.value) })}
              className="w-full accent-rose-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0% (Clean)</span>
              <span>3% (Base)</span>
              <span>15% (Heavy)</span>
            </div>
          </div>

        </div>
      ) : (
        /* WIND KNOBS */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4 bg-slate-900/50 p-4 rounded-xl border border-slate-800">
          
          {/* Wind Capacity */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300">Wind Capacity</span>
              <span className="font-mono font-bold text-cyan-400">{windParams.wind_capacity_mw} MW</span>
            </div>
            <input
              type="range"
              min="100"
              max="1000"
              step="10"
              value={windParams.wind_capacity_mw}
              onChange={(e) => setWindParams({ ...windParams, wind_capacity_mw: parseFloat(e.target.value) })}
              className="w-full accent-cyan-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>100 MW</span>
              <span>596 MW</span>
              <span>1,000 MW</span>
            </div>
          </div>

          {/* Hub Height */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300">Hub Height (m)</span>
              <span className="font-mono font-bold text-emerald-400">{windParams.hub_height_m} m</span>
            </div>
            <input
              type="range"
              min="60"
              max="160"
              step="5"
              value={windParams.hub_height_m}
              onChange={(e) => setWindParams({ ...windParams, hub_height_m: parseFloat(e.target.value) })}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>60 m</span>
              <span>100 m</span>
              <span>160 m</span>
            </div>
          </div>

          {/* Rotor Pitch Offset */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300">Blade Pitch Offset</span>
              <span className="font-mono font-bold text-amber-400">{windParams.pitch_offset_deg}°</span>
            </div>
            <input
              type="range"
              min="-5.0"
              max="15.0"
              step="0.5"
              value={windParams.pitch_offset_deg}
              onChange={(e) => setWindParams({ ...windParams, pitch_offset_deg: parseFloat(e.target.value) })}
              className="w-full accent-amber-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>-5° (Fine)</span>
              <span>0° (Base)</span>
              <span>15° (Feather)</span>
            </div>
          </div>

          {/* Cut-in Speed */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300">Cut-In Speed</span>
              <span className="font-mono font-bold text-indigo-400">{windParams.cut_in_speed_ms} m/s</span>
            </div>
            <input
              type="range"
              min="2.0"
              max="5.0"
              step="0.2"
              value={windParams.cut_in_speed_ms}
              onChange={(e) => setWindParams({ ...windParams, cut_in_speed_ms: parseFloat(e.target.value) })}
              className="w-full accent-indigo-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>2.0 m/s</span>
              <span>3.0 m/s</span>
              <span>5.0 m/s</span>
            </div>
          </div>

          {/* Air Density */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300">Air Density</span>
              <span className="font-mono font-bold text-teal-400">{windParams.air_density_kg_m3} kg/m³</span>
            </div>
            <input
              type="range"
              min="1.00"
              max="1.40"
              step="0.01"
              value={windParams.air_density_kg_m3}
              onChange={(e) => setWindParams({ ...windParams, air_density_kg_m3: parseFloat(e.target.value) })}
              className="w-full accent-teal-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>1.00 (Warm)</span>
              <span>1.225 (ISA)</span>
              <span>1.40 (Cold)</span>
            </div>
          </div>

          {/* Curtailment / Acoustic Derate */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-300">Grid Curtailment</span>
              <span className="font-mono font-bold text-rose-400">{windParams.derating_pct}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="50"
              step="5"
              value={windParams.derating_pct}
              onChange={(e) => setWindParams({ ...windParams, derating_pct: parseFloat(e.target.value) })}
              className="w-full accent-rose-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0% (Full)</span>
              <span>25%</span>
              <span>50% (Acoustic)</span>
            </div>
          </div>

        </div>
      )}

      {/* Yield Impact Scorecard */}
      {simResult && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Baseline Window Yield</span>
            <div className="text-base font-bold text-white mt-1">
              {(simResult.total_baseline_mwh ?? 0).toLocaleString()} <span className="text-xs font-normal text-slate-400">MWh</span>
            </div>
            <span className="text-[10px] text-slate-500">Unmodified Baseline Profile</span>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Simulated Window Yield</span>
            <div className="text-base font-bold text-emerald-400 mt-1">
              {(simResult.total_simulated_mwh ?? 0).toLocaleString()} <span className="text-xs font-normal text-slate-400">MWh</span>
            </div>
            <span className="text-[10px] text-slate-500">
              {activeDomain === 'solar' ? 'Transposed & Clipped' : 'Shear & Density Adjusted'}
            </span>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Yield Delta</span>
            <div className={`text-base font-bold mt-1 ${simResult.yield_change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {simResult.yield_change_pct >= 0 ? `+${simResult.yield_change_pct}%` : `${simResult.yield_change_pct}%`}
            </div>
            <span className="text-[10px] text-slate-500">
              {simResult.delta_mwh >= 0 ? `+${simResult.delta_mwh}` : simResult.delta_mwh} MWh Difference
            </span>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Physics Engine</span>
            <div className="text-base font-bold text-cyan-400 mt-1">
              {activeDomain === 'solar' ? 'pvlib Transposition' : 'windpowerlib IEC Curve'}
            </div>
            <span className="text-[10px] text-slate-500">Sub-10ms Digital Twin Loop</span>
          </div>
        </div>
      )}

      {/* Dynamic Comparison Chart */}
      <div className="space-y-2">
        <div className="flex justify-between items-center text-xs">
          <span className="font-semibold text-slate-300">
            {activeDomain === 'solar' ? 'Solar Transposition Generation Profile (MW)' : 'Wind Aerodynamic Power Generation Profile (MW)'}
          </span>
          {isSimulating && (
            <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-mono">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping"></span>
              Computing physics model...
            </span>
          )}
        </div>

        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" vertical={false} />
              <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => `${Math.round(v)} MW`} />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const pt = payload[0].payload;
                    return (
                      <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 text-xs space-y-1 shadow-xl">
                        <div className="font-semibold text-white border-b border-slate-800 pb-1">
                          Time Interval: {label}
                        </div>
                        <div className="flex justify-between gap-4 text-slate-400">
                          <span>Baseline Power:</span>
                          <span className="text-slate-200">{pt.baseline?.toFixed(1)} MW</span>
                        </div>
                        <div className="flex justify-between gap-4 text-emerald-400 font-semibold">
                          <span>Simulated Power:</span>
                          <span>{pt.simulated?.toFixed(1)} MW</span>
                        </div>
                        <div className="flex justify-between gap-4 text-cyan-400 font-semibold pt-1 border-t border-slate-800">
                          <span>Delta:</span>
                          <span>{pt.delta > 0 ? `+${pt.delta?.toFixed(1)}` : pt.delta?.toFixed(1)} MW</span>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend verticalAlign="top" align="right" iconType="circle" wrapperStyle={{ fontSize: '11px', paddingBottom: '10px' }} />

              <Line
                type="monotone"
                dataKey="baseline"
                name={`Baseline Fleet (${activeDomain === 'solar' ? '545 MW' : '596 MW'})`}
                stroke="#64748b"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="simulated"
                name="Simulated Twin Profile"
                stroke={activeDomain === 'solar' ? '#f59e0b' : '#06b6d4'}
                strokeWidth={2.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
}
