import React, { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { AdminDashboardStats } from '@/types';
import { AdminDashboardView } from './AdminDashboardView';
import { AdminLeadsView } from './AdminLeadsView';
import { AdminRegistrationsView } from './AdminRegistrationsView';
import { AdminAnalyticsView } from './AdminAnalyticsView';
import { AdminWhatsAppView } from './AdminWhatsAppView';

interface AdminPortalProps {
  onBackToSite: () => void;
}

export const AdminPortal: React.FC<AdminPortalProps> = ({ onBackToSite }) => {
  const [adminKey, setAdminKey] = useState<string>(() => {
    return sessionStorage.getItem('marathon_admin_key') || 'marathon_admin_secret_2026';
  });
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [keyInput, setKeyInput] = useState<string>(adminKey);
  const [authError, setAuthError] = useState<string | null>(null);

  // Active Navigation Tab
  const [activeTab, setActiveTab] = useState<'overview' | 'leads' | 'registrations' | 'analytics' | 'whatsapp'>('overview');

  // Stats state
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardStats = useCallback(async (keyToUse: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAdminDashboard(keyToUse);
      setStats(data);
      setIsAuthenticated(true);
      sessionStorage.setItem('marathon_admin_key', keyToUse);
    } catch (err: any) {
      setIsAuthenticated(false);
      setError(err.message || 'Authentication failed. Please verify Admin API Key.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (adminKey) {
      fetchDashboardStats(adminKey);
    } else {
      setLoading(false);
    }
  }, [adminKey, fetchDashboardStats]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyInput.trim()) {
      setAuthError('Please enter the Admin API Key.');
      return;
    }
    setAuthError(null);
    setAdminKey(keyInput.trim());
    fetchDashboardStats(keyInput.trim());
  };

  const handleLogout = () => {
    sessionStorage.removeItem('marathon_admin_key');
    setAdminKey('');
    setKeyInput('');
    setIsAuthenticated(false);
    setStats(null);
  };

  // If not authenticated, render Login / Key Entry Screen
  if (!isAuthenticated && !loading) {
    return (
      <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col justify-center items-center px-4 py-12 transition-colors">
        <div className="w-full max-w-md bg-white border border-slate-200 rounded-3xl p-8 shadow-xl space-y-6">
          <div className="text-center space-y-2">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-amber-100 text-amber-600 border border-amber-200 mb-2">
              <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h1 className="text-2xl font-black uppercase tracking-wider text-slate-900">
              Organizer Portal
            </h1>
            <p className="text-xs text-slate-600">
              Enter Admin Security Key to access registrations, leads, and revenue analytics.
            </p>
          </div>

          {(authError || error) && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs font-semibold">
              {authError || error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Admin API Key / Passcode
              </label>
              <input
                type="password"
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                placeholder="Enter admin secret key..."
                className="w-full bg-white border border-slate-300 focus:border-amber-500 rounded-xl px-4 py-3 text-sm text-slate-900 focus:outline-none transition shadow-sm"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Default local dev key: <code className="text-amber-700 font-semibold">marathon_admin_secret_2026</code>
              </p>
            </div>

            <button
              type="submit"
              className="w-full py-3 bg-amber-500 hover:bg-amber-400 text-slate-950 font-black rounded-xl text-sm uppercase tracking-wider transition shadow-md shadow-amber-500/20"
            >
              Unlock Dashboard
            </button>
          </form>

          <div className="text-center pt-2">
            <button
              onClick={onBackToSite}
              className="text-xs text-slate-500 hover:text-slate-900 font-semibold transition"
            >
              ← Back to Public Marathon Page
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col transition-colors">
      {/* Top Admin Navbar */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo & Portal Title */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-500 text-slate-950 font-black text-sm flex items-center justify-center shadow-sm">
              M
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-black text-slate-900 uppercase tracking-wider text-sm">
                  {stats?.event_name || 'City Marathon 2026'}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-amber-100 text-amber-800 border border-amber-200">
                  Admin
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition ${
                activeTab === 'overview'
                  ? 'bg-amber-500 text-slate-950 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('leads')}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition ${
                activeTab === 'leads'
                  ? 'bg-amber-500 text-slate-950 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Leads
            </button>
            <button
              onClick={() => setActiveTab('registrations')}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition ${
                activeTab === 'registrations'
                  ? 'bg-amber-500 text-slate-950 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Registrations
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition ${
                activeTab === 'analytics'
                  ? 'bg-amber-500 text-slate-950 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Analytics
            </button>
            <button
              onClick={() => setActiveTab('whatsapp')}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition ${
                activeTab === 'whatsapp'
                  ? 'bg-amber-500 text-slate-950 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              WhatsApp
            </button>
          </nav>

          {/* User Controls */}
          <div className="flex items-center gap-3">
            <button
              onClick={onBackToSite}
              className="hidden sm:inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900 font-bold uppercase tracking-wider px-3 py-1.5 rounded-lg hover:bg-slate-100 transition"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              View Site
            </button>

            <button
              onClick={handleLogout}
              className="px-3 py-1.5 bg-slate-100 hover:bg-red-50 hover:text-red-600 text-slate-600 rounded-lg text-xs font-bold uppercase tracking-wider transition border border-slate-200 hover:border-red-200"
            >
              Lock
            </button>
          </div>
        </div>

        {/* Mobile Tab Strip */}
        <div className="md:hidden flex items-center justify-around border-t border-slate-200 px-2 py-2 bg-white">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1 text-xs font-bold uppercase ${
              activeTab === 'overview' ? 'text-amber-600 border-b-2 border-amber-500' : 'text-slate-500'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('leads')}
            className={`px-3 py-1 text-xs font-bold uppercase ${
              activeTab === 'leads' ? 'text-amber-600 border-b-2 border-amber-500' : 'text-slate-500'
            }`}
          >
            Leads
          </button>
          <button
            onClick={() => setActiveTab('registrations')}
            className={`px-3 py-1 text-xs font-bold uppercase ${
              activeTab === 'registrations' ? 'text-amber-600 border-b-2 border-amber-500' : 'text-slate-500'
            }`}
          >
            Registrations
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-3 py-1 text-xs font-bold uppercase ${
              activeTab === 'analytics' ? 'text-amber-600 border-b-2 border-amber-500' : 'text-slate-500'
            }`}
          >
            Analytics
          </button>
          <button
            onClick={() => setActiveTab('whatsapp')}
            className={`px-3 py-1 text-xs font-bold uppercase ${
              activeTab === 'whatsapp' ? 'text-amber-600 border-b-2 border-amber-500' : 'text-slate-500'
            }`}
          >
            WhatsApp
          </button>
        </div>
      </header>

      {/* Main Admin Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading && !stats ? (
          <div className="text-center py-24 text-slate-500 text-sm">
            <svg className="w-10 h-10 animate-spin mx-auto text-amber-500 mb-3" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Loading admin data...
          </div>
        ) : (
          <>
            {activeTab === 'overview' && stats && (
              <AdminDashboardView
                stats={stats}
                adminKey={adminKey}
                onNavigateTab={(t) => setActiveTab(t)}
                onRefresh={() => fetchDashboardStats(adminKey)}
              />
            )}

            {activeTab === 'leads' && (
              <AdminLeadsView adminKey={adminKey} />
            )}

            {activeTab === 'registrations' && (
              <AdminRegistrationsView adminKey={adminKey} />
            )}

            {activeTab === 'analytics' && (
              <AdminAnalyticsView adminKey={adminKey} />
            )}

            {activeTab === 'whatsapp' && (
              <AdminWhatsAppView adminKey={adminKey} />
            )}
          </>
        )}
      </main>
    </div>
  );
};
