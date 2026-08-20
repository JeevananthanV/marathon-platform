import React, { useState } from 'react';
import { AdminDashboardStats } from '@/types';
import { api } from '@/lib/api';

interface AdminDashboardViewProps {
  stats: AdminDashboardStats;
  adminKey: string;
  onNavigateTab: (tab: 'leads' | 'registrations' | 'analytics') => void;
  onRefresh: () => void;
}

export const AdminDashboardView: React.FC<AdminDashboardViewProps> = ({
  stats,
  adminKey,
  onNavigateTab,
  onRefresh,
}) => {
  const [retryingZoho, setRetryingZoho] = useState<boolean>(false);
  const [zohoActionResult, setZohoActionResult] = useState<string | null>(null);

  const zoho = stats.zoho_summary;

  const handleRetryZoho = async () => {
    setRetryingZoho(true);
    setZohoActionResult(null);
    try {
      const res = await api.retryFailedZoho(adminKey, 50);
      setZohoActionResult(`Successfully processed ${res.total_processed} records (${res.successful} synced, ${res.failed} failed).`);
      onRefresh();
    } catch (err: any) {
      setZohoActionResult(`Zoho retry error: ${err.message || 'Unknown failure'}`);
    } finally {
      setRetryingZoho(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Top Header Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-slate-900 uppercase tracking-wider">
            Organizer Overview
          </h2>
          <p className="text-sm text-slate-600">
            Real-time participant counts, verified revenue, and race capacity metrics.
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 rounded-xl text-xs font-bold uppercase tracking-wider transition border border-slate-300 shadow-sm"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh Data
        </button>
      </div>

      {/* Zoho CRM Synchronization Status Banner */}
      {zoho && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-md space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-orange-100 border border-orange-200 flex items-center justify-center text-orange-600 font-black text-base">
                Z
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-slate-900 text-base">Zoho CRM Integration</h3>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                    zoho.mode === 'mock'
                      ? 'bg-amber-100 text-amber-800 border border-amber-200'
                      : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                  }`}>
                    {zoho.mode === 'mock' ? 'MOCK MODE' : 'LIVE API'}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-slate-100 text-slate-700">
                    {zoho.status}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Synchronizing participant leads, race registrations, and payment confirmations.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleRetryZoho}
                disabled={retryingZoho}
                className="px-4 py-2 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-bold rounded-xl text-xs uppercase tracking-wider transition shadow-sm flex items-center gap-2"
              >
                {retryingZoho ? (
                  <>
                    <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Syncing...
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Retry Zoho Sync
                  </>
                )}
              </button>
            </div>
          </div>

          {zohoActionResult && (
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700">
              {zohoActionResult}
            </div>
          )}

          {/* Sync Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-slate-100 text-xs">
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div className="text-slate-500 text-[11px] uppercase tracking-wider font-semibold">Synced Leads</div>
              <div className="text-lg font-black text-emerald-600 mt-1">{zoho.synced_count}</div>
            </div>
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div className="text-slate-500 text-[11px] uppercase tracking-wider font-semibold">Pending Sync</div>
              <div className="text-lg font-black text-amber-600 mt-1">{zoho.pending_count}</div>
            </div>
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div className="text-slate-500 text-[11px] uppercase tracking-wider font-semibold">Failed Sync</div>
              <div className="text-lg font-black text-rose-600 mt-1">{zoho.failed_count}</div>
            </div>
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div className="text-slate-500 text-[11px] uppercase tracking-wider font-semibold">Last Sync Attempt</div>
              <div className="text-xs font-mono text-slate-700 mt-2 truncate">
                {zoho.last_sync_attempt ? new Date(zoho.last_sync_attempt).toLocaleTimeString('en-IN') : 'None'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Leads */}
        <div
          onClick={() => onNavigateTab('leads')}
          className="bg-white border border-slate-200 hover:border-amber-400 p-5 rounded-2xl cursor-pointer transition shadow-sm hover:shadow-md group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Total Leads</span>
            <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center text-amber-700 group-hover:scale-110 transition">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-black text-slate-900">{stats.total_leads}</span>
            <span className="text-xs text-amber-600 ml-2 font-semibold">Inquiries</span>
          </div>
          <p className="mt-2 text-xs text-slate-500">Click to manage and update lead statuses →</p>
        </div>

        {/* Total Registrations */}
        <div
          onClick={() => onNavigateTab('registrations')}
          className="bg-white border border-slate-200 hover:border-cyan-400 p-5 rounded-2xl cursor-pointer transition shadow-sm hover:shadow-md group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Registrations</span>
            <div className="w-8 h-8 rounded-lg bg-cyan-100 flex items-center justify-center text-cyan-700 group-hover:scale-110 transition">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-black text-slate-900">{stats.total_registrations}</span>
            <span className="text-xs text-cyan-600 ml-2 font-semibold">Total Orders</span>
          </div>
          <div className="mt-2 flex items-center gap-3 text-xs">
            <span className="text-emerald-600 font-semibold">{stats.paid_registrations} Confirmed</span>
            <span className="text-amber-600 font-semibold">{stats.pending_payments} Pending</span>
          </div>
        </div>

        {/* Total Verified Revenue */}
        <div
          onClick={() => onNavigateTab('analytics')}
          className="bg-white border border-slate-200 hover:border-emerald-400 p-5 rounded-2xl cursor-pointer transition shadow-sm hover:shadow-md group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Verified Revenue</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-700 group-hover:scale-110 transition">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-black text-emerald-600">
              ₹{stats.revenue_inr.toLocaleString('en-IN')}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            From {stats.paid_participants_count} verified payments (Razorpay)
          </p>
        </div>

        {/* Average Registration Value */}
        <div
          onClick={() => onNavigateTab('analytics')}
          className="bg-white border border-slate-200 hover:border-purple-400 p-5 rounded-2xl cursor-pointer transition shadow-sm hover:shadow-md group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Avg Value (AOV)</span>
            <div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center text-purple-700 group-hover:scale-110 transition">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-black text-purple-600">
              ₹{stats.average_order_value_inr.toFixed(0)}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500">Per confirmed runner</p>
        </div>
      </div>

      {/* Race Category Capacities & Utilization */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-md">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-black text-slate-900 uppercase tracking-wider">
              Race Category Capacity & Slots
            </h3>
            <p className="text-xs text-slate-500 mt-1">Live slot counters across all distances</p>
          </div>
          <button
            onClick={() => onNavigateTab('registrations')}
            className="text-xs text-amber-700 hover:text-amber-800 font-bold uppercase tracking-wider"
          >
            View Category Registrations →
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {stats.categories.map((cat) => (
            <div
              key={cat.code}
              className="bg-slate-50 border border-slate-200 rounded-xl p-5 relative overflow-hidden"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-black bg-amber-100 text-amber-800 border border-amber-200 mb-2">
                    {cat.code}
                  </span>
                  <h4 className="text-base font-bold text-slate-900">{cat.title}</h4>
                  <p className="text-xs text-slate-500">₹{cat.price_inr} per runner</p>
                </div>
                <div className="text-right">
                  <div className="text-xl font-black text-slate-900">{cat.paid_count}</div>
                  <div className="text-xs text-slate-500">Paid / {cat.max_capacity} max</div>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mt-4">
                <div className="flex justify-between text-xs text-slate-500 mb-1">
                  <span>Capacity Filled</span>
                  <span className="font-semibold text-slate-700">{cat.fill_percentage}%</span>
                </div>
                <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      cat.fill_percentage > 85
                        ? 'bg-red-500'
                        : cat.fill_percentage > 50
                        ? 'bg-amber-500'
                        : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, cat.fill_percentage))}%` }}
                  />
                </div>
              </div>

              {/* Metrics footer */}
              <div className="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between text-xs">
                <span className="text-slate-600">
                  <strong className="text-slate-900">{cat.slots_remaining}</strong> slots left
                </span>
                <span className="text-emerald-600 font-bold">
                  ₹{cat.revenue_inr.toLocaleString('en-IN')} rev
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Registrations Live Table */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-md">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-black text-slate-900 uppercase tracking-wider">
              Recent Registrations
            </h3>
            <p className="text-xs text-slate-500 mt-1">Latest runner sign-ups received</p>
          </div>
          <button
            onClick={() => onNavigateTab('registrations')}
            className="text-xs text-amber-700 hover:text-amber-800 font-bold uppercase tracking-wider"
          >
            All Registrations →
          </button>
        </div>

        {stats.recent_registrations.length === 0 ? (
          <div className="text-center py-10 text-slate-400 text-sm">
            No registrations received yet. Test a registration from the main page.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="text-[11px] uppercase tracking-wider text-slate-700 bg-slate-100 border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Reg Code</th>
                  <th className="py-3 px-4">Participant</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Amount</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Zoho Sync</th>
                  <th className="py-3 px-4">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {stats.recent_registrations.map((reg) => (
                  <tr key={reg.registration_id} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-4 font-mono font-bold text-amber-700">
                      {reg.registration_code}
                      {reg.bib_number && (
                        <span className="block text-[10px] text-slate-500">BIB: {reg.bib_number}</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-900">{reg.participant_name}</div>
                      <div className="text-slate-500 text-[11px]">{reg.email}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-bold border border-slate-200">
                        {reg.category_code || reg.category}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-900">
                      ₹{reg.amount_inr}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                          reg.status === 'CONFIRMED'
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            : 'bg-amber-100 text-amber-800 border border-amber-200'
                        }`}
                      >
                        {reg.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                          reg.zoho_sync_status === 'SYNCED'
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            : reg.zoho_sync_status === 'FAILED'
                            ? 'bg-red-100 text-red-800 border border-red-200'
                            : 'bg-slate-100 text-slate-600 border border-slate-200'
                        }`}
                      >
                        {reg.zoho_sync_status || 'PENDING'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {reg.created_at ? new Date(reg.created_at).toLocaleDateString('en-IN') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
