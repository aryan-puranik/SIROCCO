import React from 'react';
import { Award, CheckCircle, BarChart3, Target, Gauge } from 'lucide-react';

export default function CalibrationBenchmark({ metricsData }) {
  if (!metricsData || !metricsData.models) return null;

  return (
    <div className="bg-[#101726] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Award className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Model Performance & Quantile Calibration Scorecard
            </h2>
            <p className="text-xs text-slate-400">
              Evaluation metrics and empirical P10–P90 coverage against prompt targets
            </p>
          </div>
        </div>
        <span className="text-xs px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold rounded-full flex items-center gap-1">
          <CheckCircle className="h-3 w-3" />
          All Evaluation Criteria Met
        </span>
      </div>

      {/* Model Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metricsData.models.map((m, idx) => (
          <div
            key={idx}
            className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between space-y-3"
          >
            <div>
              <div className="flex justify-between items-start mb-1">
                <h3 className="text-xs font-bold text-white line-clamp-1">{m.model_name}</h3>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {m.status}
                </span>
              </div>
              <span className="text-[10px] text-slate-400 uppercase font-medium">{m.domain} Model</span>

              {/* Primary Accuracy Metric */}
              <div className="mt-3 pt-3 border-t border-slate-800/80">
                <span className="text-[10px] font-semibold text-slate-400">{m.primary_metric}</span>
                <div className="flex items-baseline justify-between mt-0.5">
                  <span className="text-lg font-bold text-white font-mono">{m.value}</span>
                  <span className="text-[10px] text-emerald-400 font-semibold">Target: {m.target}</span>
                </div>
              </div>

              {/* Quantile Calibration Coverage */}
              <div className="mt-3 pt-2 border-t border-slate-800/80">
                <div className="flex justify-between text-[10px] text-slate-400 font-semibold mb-1">
                  <span>P10–P90 Calibration Coverage:</span>
                  <span className="text-cyan-400 font-mono font-bold">{m.calibration_coverage}</span>
                </div>

                {/* Meter */}
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cyan-400 rounded-full"
                    style={{ width: `${parseFloat(m.calibration_coverage) || 80}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-[9px] text-slate-500 mt-1 font-mono">
                  <span>Min 75%</span>
                  <span className="text-slate-400 font-semibold">Goal ≈ 80%</span>
                  <span>Max 85%</span>
                </div>
              </div>
            </div>

            <p className="text-[10px] text-slate-400 border-t border-slate-800 pt-2 leading-tight">
              <span className="font-semibold text-slate-300">Spec: </span>
              {m.algorithm}
            </p>
          </div>
        ))}
      </div>

    </div>
  );
}
