import React from 'react';

const VARIANTS = {
  normal: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  critical: 'bg-rose-50 text-rose-700 border-rose-200',
  info: 'bg-blue-50 text-blue-700 border-blue-200',
  neutral: 'bg-slate-100 text-slate-700 border-slate-200',
  solar: 'bg-amber-50 text-amber-700 border-amber-300',
  wind: 'bg-teal-50 text-teal-700 border-teal-300',
  surplus: 'bg-purple-50 text-purple-700 border-purple-200',
  shortfall: 'bg-red-50 text-red-700 border-red-200',
};

export default function Badge({ 
  children, 
  variant = 'normal', 
  dot = false, 
  pulse = false,
  className = '' 
}) {
  const variantClasses = VARIANTS[variant] || VARIANTS.normal;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${variantClasses} ${className}`}>
      {dot && (
        <span className="relative flex h-2 w-2">
          {pulse && (
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
              variant === 'critical' ? 'bg-rose-400' :
              variant === 'warning' ? 'bg-amber-400' :
              'bg-emerald-400'
            }`} />
          )}
          <span className={`relative inline-flex rounded-full h-2 w-2 ${
            variant === 'critical' ? 'bg-rose-500' :
            variant === 'warning' ? 'bg-amber-500' :
            variant === 'info' ? 'bg-blue-500' :
            'bg-emerald-500'
          }`} />
        </span>
      )}
      {children}
    </span>
  );
}
