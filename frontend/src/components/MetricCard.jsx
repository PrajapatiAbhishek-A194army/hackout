import React from 'react';
import { TrendingUp, TrendingDown, Minus, Info } from 'lucide-react';

export default function MetricCard({
  title,
  value,
  unit = '',
  subtitle,
  trend,
  badge,
  icon: Icon,
  iconBg = 'bg-emerald-50 text-emerald-600',
  confidence,
  explain,
  className = '',
}) {
  return (
    <div className={`card-enterprise p-5 flex flex-col justify-between relative group ${className}`}>
      <div>
        {/* Card Header */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2.5">
            {Icon && (
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${iconBg}`}>
                <Icon className="w-5 h-5" />
              </div>
            )}
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
                {title}
              </span>
              {subtitle && (
                <span className="text-[11px] text-slate-400 block font-normal">
                  {subtitle}
                </span>
              )}
            </div>
          </div>
          {badge && <div className="shrink-0">{badge}</div>}
        </div>

        {/* Primary Value Display */}
        <div className="flex items-baseline gap-1.5 mt-2">
          <span className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
            {value}
          </span>
          {unit && (
            <span className="text-sm font-semibold text-slate-500">
              {unit}
            </span>
          )}
        </div>
      </div>

      {/* Card Footer: Trend & Confidence */}
      <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs">
        {trend ? (
          <div className="flex items-center gap-1">
            {trend.direction === 'up' && (
              <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
            )}
            {trend.direction === 'down' && (
              <TrendingDown className="w-3.5 h-3.5 text-rose-600" />
            )}
            {trend.direction === 'neutral' && (
              <Minus className="w-3.5 h-3.5 text-slate-400" />
            )}
            <span className={`font-semibold ${
              trend.direction === 'up' ? 'text-emerald-700' :
              trend.direction === 'down' ? 'text-rose-700' :
              'text-slate-600'
            }`}>
              {trend.value}
            </span>
            <span className="text-slate-400 text-[11px]">{trend.text}</span>
          </div>
        ) : <div />}

        {confidence !== undefined && (
          <div className="flex items-center gap-1 text-[11px] font-medium text-slate-500 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
            <span>Conf:</span>
            <span className="font-bold text-emerald-700">{confidence}</span>
          </div>
        )}
      </div>

      {/* Explainability footnote if present */}
      {explain && (
        <div className="mt-2 text-[11px] text-slate-500 bg-emerald-50/50 rounded p-2 border border-emerald-100 flex items-start gap-1.5">
          <Info className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
          <span className="leading-snug">{explain}</span>
        </div>
      )}
    </div>
  );
}
