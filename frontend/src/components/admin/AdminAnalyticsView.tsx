import React, { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { AdminAnalyticsResponse } from '@/types';

interface AdminAnalyticsViewProps {
  adminKey: string;
}

export const AdminAnalyticsView: React.FC<AdminAnalyticsViewProps> = ({ adminKey }) => {
  const [analytics, setAnalytics] = useState<AdminAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAdminAnalytics(adminKey);
      setAnalytics(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch analytics data');
    } finally {
      setLoading(false);
    }
  }, [adminKey]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  if (loading) {
    return (
      <div className="text-center py-20 text-slate-500 text-sm">
        <svg className="w-8 h-8 animate-spin mx-auto text-amber-500 mb-3" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        Loading analytics & conversion funnel...
      </div>
    );
  }

  if (error || !analytics) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-2xl text-red-700 text-sm flex items-center justify-between">
        <span>{error || 'No analytics data available'}</span>
        <button
          onClick={fetchAnalytics}
          className="px-4 py-1.5 bg-red-100 hover:bg-red-200 rounded-lg font-bold uppercase text-xs transition"
        >
          Retry
        </button>
      </div>
    );
  }

  const { funnel, categories, utm_sources } = analytics;

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-slate-900 uppercase tracking-wider">
            Marketing & Conversion Analytics
          </h2>
          <p className="text-sm text-slate-600">
            Conversion funnel progression, acquisition attribution, and category breakdown.
          </p>
        </div>
        <button
          onClick={fetchAnalytics}
          className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 rounded-xl text-xs font-bold uppercase tracking-wider transition border border-slate-300 shadow-sm"
        >
          Refresh Analytics
        </button>
      </div>

      {/* 1. Conversion Funnel Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-md space-y-6">
        <div>
          <h3 className="text-lg font-black text-slate-900 uppercase tracking-wider">
            End-to-End Conversion Funnel
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Tracking participant progression from initial lead inquiry to verified payment.
          </p>
        </div>

        {/* 3-Stage Visual Funnel */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative">
          {/* Stage 1: Leads */}
          <div className="bg-slate-50 border border-amber-300 rounded-xl p-5 relative overflow-hidden">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-700">Stage 1</span>
              <span className="text-xs text-slate-500 font-mono">100% Baseline</span>
            </div>
            <div className="text-2xl font-black text-slate-900">{funnel.total_leads}</div>
            <div className="text-sm font-semibold text-slate-800 mt-1">Total Leads / Inquiries</div>
            <p className="text-[11px] text-slate-500 mt-2">
              All unique participants captured in database
            </p>
          </div>

          {/* Stage 2: Registered */}
          <div className="bg-slate-50 border border-cyan-300 rounded-xl p-5 relative overflow-hidden">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-700">Stage 2</span>
              <span className="text-xs font-bold text-cyan-700 font-mono">
                {funnel.lead_to_reg_rate_pct}% of Leads
              </span>
            </div>
            <div className="text-2xl font-black text-slate-900">{funnel.total_registered}</div>
            <div className="text-sm font-semibold text-slate-800 mt-1">Orders Initiated</div>
            <p className="text-[11px] text-slate-500 mt-2">
              Participants who selected a race category
            </p>
          </div>

          {/* Stage 3: Paid & Confirmed */}
          <div className="bg-slate-50 border border-emerald-300 rounded-xl p-5 relative overflow-hidden">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-700">Stage 3</span>
              <span className="text-xs font-bold text-emerald-700 font-mono">
                {funnel.reg_to_paid_rate_pct}% of Reg
              </span>
            </div>
            <div className="text-2xl font-black text-emerald-600">{funnel.total_paid}</div>
            <div className="text-sm font-semibold text-slate-800 mt-1">Confirmed & Paid</div>
            <p className="text-[11px] text-slate-500 mt-2">
              Verified Razorpay payments with BIBs allocated
            </p>
          </div>
        </div>

        {/* Funnel Summary Bar */}
        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div>
            <span className="text-slate-600">Lead → Registration Conversion:</span>
            <strong className="text-cyan-700 ml-2 font-mono text-sm">
              {funnel.lead_to_reg_rate_pct}%
            </strong>
          </div>
          <div>
            <span className="text-slate-600">Registration → Payment Conversion:</span>
            <strong className="text-amber-700 ml-2 font-mono text-sm">
              {funnel.reg_to_paid_rate_pct}%
            </strong>
          </div>
          <div>
            <span className="text-slate-600">Overall Acquisition Conversion:</span>
            <strong className="text-emerald-700 ml-2 font-mono text-sm">
              {funnel.overall_conversion_rate_pct}%
            </strong>
          </div>
        </div>
      </div>

      {/* 2. Marketing / UTM Attribution Table */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-md space-y-4">
        <div>
          <h3 className="text-lg font-black text-slate-900 uppercase tracking-wider">
            Marketing Attribution by Source (UTM)
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Analyze which ad channels (Instagram, Facebook, Google Ads, Direct) deliver highest ROI.
          </p>
        </div>

        {utm_sources.length === 0 ? (
          <div className="text-center py-10 text-slate-400 text-xs">
            No attribution data recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="text-[11px] uppercase tracking-wider text-slate-700 bg-slate-100 border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Traffic / Campaign Source</th>
                  <th className="py-3 px-4 text-center">Inquiries</th>
                  <th className="py-3 px-4 text-center">Paid Runners</th>
                  <th className="py-3 px-4 text-center">Conversion Rate</th>
                  <th className="py-3 px-4 text-right">Revenue Generated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {utm_sources.map((item) => (
                  <tr key={item.source} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-4">
                      <span className="inline-block px-2.5 py-1 rounded-md bg-purple-50 text-purple-800 border border-purple-200 font-bold uppercase font-mono text-xs">
                        {item.source}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center font-bold text-slate-900">
                      {item.leads_count}
                    </td>
                    <td className="py-3 px-4 text-center font-bold text-emerald-600">
                      {item.paid_count}
                    </td>
                    <td className="py-3 px-4 text-center font-mono font-bold text-cyan-700">
                      {item.conversion_rate_pct}%
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900 text-sm">
                      ₹{item.revenue_inr.toLocaleString('en-IN')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 3. Category Performance & Revenue Share */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-md space-y-4">
        <div>
          <h3 className="text-lg font-black text-slate-900 uppercase tracking-wider">
            Category Share & Revenue Distribution
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Revenue breakdown across 5K, 10K, and 21K Half Marathon.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {categories.map((c) => (
            <div
              key={c.category_code}
              className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-3"
            >
              <div className="flex justify-between items-center">
                <span className="px-2.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200 font-black text-xs">
                  {c.category_code}
                </span>
                <span className="text-xs font-mono text-slate-500">
                  {c.share_pct}% Volume Share
                </span>
              </div>
              <h4 className="text-base font-bold text-slate-900">{c.category_title}</h4>
              <div className="pt-2 border-t border-slate-200 flex justify-between items-center text-xs">
                <span className="text-slate-500">{c.paid_count} Paid Runners</span>
                <span className="text-emerald-600 font-bold text-sm">
                  ₹{c.revenue_inr.toLocaleString('en-IN')}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
