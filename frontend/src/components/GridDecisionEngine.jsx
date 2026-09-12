import React from 'react';
import { BatteryCharging, ShieldAlert, Wrench, Zap, CheckCircle2, ArrowRight } from 'lucide-react';

export default function GridDecisionEngine({ recommendations }) {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="bg-[#101726] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
            <BatteryCharging className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Intelligent Grid Decision & Dispatch Engine
            </h2>
            <p className="text-xs text-slate-400">
              Probabilistic generation-informed storage dispatch, curtailment risk mitigation, and outage scheduling
            </p>
          </div>
        </div>
        <span className="text-xs px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold rounded-full">
          Live Dispatch Advisory
        </span>
      </div>

      {/* Grid of Recommendation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {recommendations.map((rec) => {
          const isBess = rec.recommendation_type.includes('BESS');
          const isCurtail = rec.recommendation_type.includes('CURTAILMENT');
          const isMaint = rec.recommendation_type.includes('MAINTENANCE');

          return (
            <div
              key={rec.id}
              className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    {rec.site_name}
                  </span>
                  <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-bold">
                    <span>Confidence:</span>
                    <span className="bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded text-[11px]">
                      {Math.round(rec.confidence * 100)}%
                    </span>
                  </div>
                </div>

                <div className="flex items-start gap-2.5 my-2">
                  <div className="p-2 rounded-lg bg-slate-800 text-emerald-400 mt-0.5">
                    {isBess ? (
                      <BatteryCharging className="h-4 w-4" />
                    ) : isCurtail ? (
                      <ShieldAlert className="h-4 w-4 text-amber-400" />
                    ) : isMaint ? (
                      <Wrench className="h-4 w-4 text-cyan-400" />
                    ) : (
                      <Zap className="h-4 w-4" />
                    )}
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-white">{rec.action}</h3>
                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{rec.rationale}</p>
                  </div>
                </div>
              </div>

              <div className="pt-3 mt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                <div className="text-slate-400">
                  Impact: <span className="font-semibold text-white">{rec.impact_mw} MW Dispatch</span>
                </div>
                <div className="flex items-center gap-1 text-emerald-400 font-medium cursor-pointer hover:underline">
                  <span>Authorize Setpoint</span>
                  <ArrowRight className="h-3 w-3" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
}
