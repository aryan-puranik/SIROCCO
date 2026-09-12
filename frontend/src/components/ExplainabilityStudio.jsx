import React from 'react';
import { HelpCircle, ArrowUpRight, ArrowDownRight, Minus, Sparkles, Compass } from 'lucide-react';

export default function ExplainabilityStudio({ data, isLoading }) {
  if (isLoading) {
    return (
      <div className="bg-[#101726] border border-slate-800 rounded-xl p-8 flex items-center justify-center min-h-[300px]">
        <div className="flex flex-col items-center gap-2">
          <div className="h-6 w-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs text-slate-400">Computing feature attributions...</span>
        </div>
      </div>
    );
  }

  if (!data || !data.top_features) return null;

  return (
    <div className="bg-[#101726] border border-slate-800 rounded-xl p-5 shadow-sm space-y-5">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Model Explainability & SHAP Studio
            </h2>
            <p className="text-xs text-slate-400">
              Domain attribution analysis & physical feature importances for {data.site_name}
            </p>
          </div>
        </div>
        <span className="text-xs px-2.5 py-1 bg-slate-900 border border-slate-700/80 rounded-full text-slate-300 font-medium">
          Domain: <span className="text-emerald-400 font-semibold uppercase">{data.model_type}</span>
        </span>
      </div>

      {/* Feature Importance Bars */}
      <div className="space-y-3">
        {data.top_features.map((item, idx) => {
          const isPositive = item.impact_direction === 'positive';
          const isNegative = item.impact_direction === 'negative';

          return (
            <div key={idx} className="bg-slate-900/60 border border-slate-800/80 rounded-lg p-3 hover:border-slate-700 transition-colors">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-200">{item.feature}</span>
                  <span
                    className={`inline-flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                      isPositive
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : isNegative
                        ? 'bg-rose-500/10 text-rose-400'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {isPositive && <ArrowUpRight className="h-3 w-3" />}
                    {isNegative && <ArrowDownRight className="h-3 w-3" />}
                    {item.impact_direction}
                  </span>
                </div>
                <span className="text-xs font-mono font-bold text-white">{item.importance}%</span>
              </div>

              {/* Progress Bar */}
              <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    isPositive ? 'bg-emerald-500' : isNegative ? 'bg-rose-500' : 'bg-cyan-500'
                  }`}
                  style={{ width: `${Math.min(100, item.importance * 2.2)}%` }}
                ></div>
              </div>

              {/* Physical Context Description */}
              <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">{item.description}</p>
            </div>
          );
        })}
      </div>

      {/* Physics Insights */}
      {data.physics_insights && data.physics_insights.length > 0 && (
        <div className="pt-3 border-t border-slate-800">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-2">
            <Compass className="h-3.5 w-3.5 text-cyan-400" />
            <span>Physics-Informed Domain Findings</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
            {data.physics_insights.map((insight, idx) => (
              <div key={idx} className="bg-slate-900/40 border border-slate-800/80 rounded-lg p-2.5 text-[11px] text-slate-300 leading-normal">
                {insight}
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
