import React, { useState } from 'react';
import { 
  X, 
  Zap, 
  Building2, 
  SunMedium, 
  TrendingUp, 
  ShieldCheck, 
  Lock, 
  Mail, 
  User, 
  Building,
  Check,
  AlertCircle,
  Sparkles,
  ArrowRight,
  KeyRound
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function AuthModal({ isOpen, onClose, initialMode = 'login', initialRole = 'grid-operator' }) {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState(initialMode); // 'login' | 'signup'
  const [selectedRole, setSelectedRole] = useState(initialRole);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    organization: ''
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const roleOptions = [
    {
      id: 'grid-operator',
      title: 'Grid Operator',
      desc: 'National/State Load Despatch, balancing authority & reserve dispatch',
      icon: Zap,
      accent: 'emerald',
      bgClass: 'hover:border-emerald-500 hover:bg-emerald-50/40',
      activeClass: 'border-emerald-500 bg-emerald-50/60 ring-2 ring-emerald-500/20',
      iconColor: 'text-emerald-600 bg-emerald-100'
    },
    {
      id: 'utility',
      title: 'Utility Company (DISCOM)',
      desc: 'Power procurement, duck curve shortfall & DAM bidding',
      icon: Building2,
      accent: 'amber',
      bgClass: 'hover:border-amber-500 hover:bg-amber-50/40',
      activeClass: 'border-amber-500 bg-amber-50/60 ring-2 ring-amber-500/20',
      iconColor: 'text-amber-600 bg-amber-100'
    },
    {
      id: 'plant-owner',
      title: 'Renewable Plant Owner (IPP)',
      desc: 'Solar/wind farm output, CUF, inverter loss & maintenance windows',
      icon: SunMedium,
      accent: 'blue',
      bgClass: 'hover:border-blue-500 hover:bg-blue-50/40',
      activeClass: 'border-blue-500 bg-blue-50/60 ring-2 ring-blue-500/20',
      iconColor: 'text-blue-600 bg-blue-100'
    },
    {
      id: 'energy-trader',
      title: 'Energy Trader & Analyst',
      desc: 'Market clearing prices (MCP ₹/kWh), DAM/RTM arbitrage & congestion',
      icon: TrendingUp,
      accent: 'purple',
      bgClass: 'hover:border-purple-500 hover:bg-purple-50/40',
      activeClass: 'border-purple-500 bg-purple-50/60 ring-2 ring-purple-500/20',
      iconColor: 'text-purple-600 bg-purple-100'
    }
  ];

  // Quick 1-click test credentials
  const demoAccounts = [
    { role: 'grid-operator', label: 'Grid Operator', email: 'operator@gridflow.ai', pass: 'OperatorPassword@123' },
    { role: 'utility', label: 'Utility (DISCOM)', email: 'utility@gridflow.ai', pass: 'UtilityPassword@123' },
    { role: 'plant-owner', label: 'Plant Owner (IPP)', email: 'plantowner@gridflow.ai', pass: 'PlantPassword@123' },
    { role: 'energy-trader', label: 'Energy Trader', email: 'trader@gridflow.ai', pass: 'TraderPassword@123' }
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (mode === 'login') {
        await login(formData.email, formData.password);
      } else {
        await signup({
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name,
          role: selectedRole,
          organization: formData.organization
        });
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async (account) => {
    setError(null);
    setLoading(true);
    try {
      await login(account.email, account.pass);
      onClose();
    } catch (err) {
      setError(err.message || 'Demo login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 animate-fadeIn">
      <div className="relative w-full max-w-xl bg-white rounded-3xl shadow-2xl border border-slate-200/80 overflow-hidden">
        
        {/* Header Ribbon */}
        <div className="bg-gradient-to-r from-emerald-800 via-teal-800 to-slate-900 text-white p-6 sm:p-8 relative">
          <button
            onClick={onClose}
            className="absolute top-5 right-5 p-2 rounded-full text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2.5 mb-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-400/40 flex items-center justify-center text-emerald-300">
              <Zap className="w-4 h-4" />
            </div>
            <span className="text-xs uppercase tracking-wider font-bold text-emerald-300">
              Enterprise Access Control
            </span>
          </div>

          <h2 className="text-2xl font-bold tracking-tight">
            {mode === 'login' ? 'Sign In to RenewableAI Console' : 'Create Industry Stakeholder Account'}
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-md">
            {mode === 'login'
              ? 'Access real-time grid telemetry, ML forecasts, and role-tailored decision workspaces.'
              : 'Select your operational role to initialize tailored telemetry, risk thresholds, and actions.'}
          </p>

          {/* Mode Switcher Tabs */}
          <div className="flex items-center gap-2 mt-5 bg-black/20 p-1 rounded-xl w-fit border border-white/10 text-xs">
            <button
              type="button"
              onClick={() => { setMode('login'); setError(null); }}
              className={`px-4 py-1.5 font-semibold rounded-lg transition-all ${
                mode === 'login'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setMode('signup'); setError(null); }}
              className={`px-4 py-1.5 font-semibold rounded-lg transition-all ${
                mode === 'signup'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              Register New Account
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 sm:p-8 space-y-6">
          {error && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-rose-700 animate-shake">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            
            {/* SIGNUP ONLY: Role Selection Cards */}
            {mode === 'signup' && (
              <div className="space-y-2.5">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Select Your Operational Role <span className="text-rose-500">*</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {roleOptions.map((role) => {
                    const Icon = role.icon;
                    const isSelected = selectedRole === role.id;
                    return (
                      <div
                        key={role.id}
                        onClick={() => setSelectedRole(role.id)}
                        className={`cursor-pointer p-3 rounded-xl border text-left transition-all ${role.bgClass} ${
                          isSelected ? role.activeClass : 'border-slate-200 bg-white'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-1.5">
                          <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${role.iconColor}`}>
                            <Icon className="w-4 h-4" />
                          </div>
                          {isSelected && (
                            <div className="w-4 h-4 rounded-full bg-emerald-600 text-white flex items-center justify-center">
                              <Check className="w-2.5 h-2.5" />
                            </div>
                          )}
                        </div>
                        <div className="font-bold text-xs text-slate-900">{role.title}</div>
                        <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">{role.desc}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Common Form Fields */}
            {mode === 'signup' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Full Name <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      required
                      placeholder="e.g. Priya Sharma"
                      value={formData.full_name}
                      onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                      className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Organization / Entity
                  </label>
                  <div className="relative">
                    <Building className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      placeholder="e.g. Northern Regional SLDC"
                      value={formData.organization}
                      onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                      className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                    />
                  </div>
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Corporate Email Address <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="email"
                  required
                  placeholder="name@organization.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Password <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white font-bold text-xs shadow-sm flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              {loading ? (
                <span>Authenticating with JWT...</span>
              ) : (
                <>
                  <span>{mode === 'login' ? 'Sign In & Launch Dashboard' : 'Complete Registration & Open Dashboard'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Logins Ribbon */}
          <div className="pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5 text-emerald-600" />
                Quick 1-Click Role Login (Testing & Judging)
              </span>
              <span className="text-[10px] text-slate-400">Pre-seeded JWT</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {demoAccounts.map((demo) => (
                <button
                  key={demo.role}
                  type="button"
                  onClick={() => handleDemoLogin(demo)}
                  className="px-2.5 py-1.5 bg-slate-50 hover:bg-emerald-50 border border-slate-200 hover:border-emerald-300 rounded-lg text-left transition-colors group"
                >
                  <div className="text-[11px] font-bold text-slate-800 group-hover:text-emerald-700 truncate">
                    {demo.label}
                  </div>
                  <div className="text-[10px] text-slate-400 group-hover:text-emerald-600">
                    Instant Demo
                  </div>
                </button>
              ))}
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
