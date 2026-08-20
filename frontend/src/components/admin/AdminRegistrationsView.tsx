import React, { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { AdminRegistrationItem } from '@/types';

interface AdminRegistrationsViewProps {
  adminKey: string;
}

export const AdminRegistrationsView: React.FC<AdminRegistrationsViewProps> = ({ adminKey }) => {
  const [registrations, setRegistrations] = useState<AdminRegistrationItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);

  // Filters, Sorting & Pagination
  const [search, setSearch] = useState<string>('');
  const [category, setCategory] = useState<string>('ALL');
  const [status, setStatus] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<string>('desc');
  const [page, setPage] = useState<number>(1);
  const pageSize = 20;

  const fetchRegistrations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getAdminRegistrations(adminKey, {
        search: search.trim() || undefined,
        category: category !== 'ALL' ? category : undefined,
        status: status !== 'ALL' ? status : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        page_size: pageSize,
      });
      setRegistrations(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch registrations');
    } finally {
      setLoading(false);
    }
  }, [adminKey, search, category, status, sortBy, sortOrder, page]);

  useEffect(() => {
    fetchRegistrations();
  }, [fetchRegistrations]);

  const handleSyncRegistration = async (regId: string) => {
    setSyncingId(regId);
    try {
      await api.syncZohoRegistration(adminKey, regId);
      // Refresh list to show updated status
      fetchRegistrations();
    } catch (err: any) {
      alert(`Zoho sync failed: ${err.message || 'Unknown error'}`);
    } finally {
      setSyncingId(null);
    }
  };

  const exportUrl = api.getExportRegistrationsUrl(adminKey);
  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Header & CSV Export */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-slate-900 uppercase tracking-wider">
            Registration Management
          </h2>
          <p className="text-sm text-slate-600">
            Search, inspect, and export all marathon registrations, BIB assignments, and Zoho sync statuses.
          </p>
        </div>

        <a
          href={exportUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold uppercase tracking-wider transition shadow-md"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Export Registrations CSV
        </a>
      </div>

      {/* Filter and Control Bar */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search Box */}
          <div className="relative md:col-span-2">
            <input
              type="text"
              placeholder="Search by Code (MX26-), BIB, Runner Name, Email..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full bg-white border border-slate-300 focus:border-amber-500 rounded-xl px-4 py-2.5 pl-10 text-sm text-slate-900 placeholder-slate-400 focus:outline-none transition shadow-sm"
            />
            <svg
              className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          {/* Category Dropdown */}
          <div>
            <select
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                setPage(1);
              }}
              className="w-full bg-white border border-slate-300 text-slate-800 text-sm rounded-xl px-3 py-2.5 focus:outline-none shadow-sm"
            >
              <option value="ALL">All Categories</option>
              <option value="5K">5K Fun Run</option>
              <option value="10K">10K Challenge</option>
              <option value="21K">21K Half Marathon</option>
            </select>
          </div>

          {/* Registration Status Dropdown */}
          <div>
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
              className="w-full bg-white border border-slate-300 text-slate-800 text-sm rounded-xl px-3 py-2.5 focus:outline-none shadow-sm"
            >
              <option value="ALL">All Statuses</option>
              <option value="CONFIRMED">CONFIRMED</option>
              <option value="PENDING">PENDING</option>
              <option value="CANCELLED">CANCELLED</option>
            </select>
          </div>
        </div>

        {/* Sorting controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100 text-xs">
          <div className="flex items-center gap-3">
            <span className="text-slate-500 font-bold uppercase tracking-wider">Sort By:</span>
            <button
              onClick={() => {
                if (sortBy === 'created_at') {
                  setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                } else {
                  setSortBy('created_at');
                  setSortOrder('desc');
                }
              }}
              className={`px-3 py-1 rounded-lg font-semibold transition ${
                sortBy === 'created_at' ? 'bg-amber-500 text-slate-950 shadow-sm' : 'bg-slate-100 text-slate-700 border border-slate-200'
              }`}
            >
              Date {sortBy === 'created_at' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
            </button>
            <button
              onClick={() => {
                if (sortBy === 'registration_code') {
                  setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                } else {
                  setSortBy('registration_code');
                  setSortOrder('asc');
                }
              }}
              className={`px-3 py-1 rounded-lg font-semibold transition ${
                sortBy === 'registration_code' ? 'bg-amber-500 text-slate-950 shadow-sm' : 'bg-slate-100 text-slate-700 border border-slate-200'
              }`}
            >
              Reg Code {sortBy === 'registration_code' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
            </button>
          </div>

          <button
            onClick={fetchRegistrations}
            className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg font-bold uppercase tracking-wider transition border border-slate-200"
          >
            Refresh List
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Registrations Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="text-center py-16 text-slate-500 text-sm">
            <svg className="w-8 h-8 animate-spin mx-auto text-amber-500 mb-3" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Loading registrations...
          </div>
        ) : registrations.length === 0 ? (
          <div className="text-center py-16 text-slate-400 text-sm">
            No registrations found matching current query.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="text-[11px] uppercase tracking-wider text-slate-700 bg-slate-100 border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Registration ID</th>
                  <th className="py-3 px-4">BIB</th>
                  <th className="py-3 px-4">Participant</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Amount</th>
                  <th className="py-3 px-4">Payment</th>
                  <th className="py-3 px-4">Reg Status</th>
                  <th className="py-3 px-4">Zoho Sync</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {registrations.map((reg) => (
                  <tr key={reg.registration_id} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-4 font-mono font-bold text-amber-700">
                      {reg.registration_code}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">
                      {reg.bib_number || <span className="text-slate-400 font-normal">Pending</span>}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-900 text-sm">{reg.participant_name}</div>
                      <div className="text-slate-500 font-mono text-[11px]">{reg.email}</div>
                      <div className="text-slate-500 font-mono text-[10px]">{reg.phone}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-bold border border-slate-200">
                        {reg.category_code}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-900">
                      ₹{reg.amount_inr}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                          reg.payment_status === 'SUCCESS'
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            : 'bg-amber-100 text-amber-800 border border-amber-200'
                        }`}
                      >
                        {reg.payment_status}
                      </span>
                      {reg.razorpay_payment_id && (
                        <div className="text-[10px] text-slate-400 font-mono mt-0.5 truncate max-w-[100px]">
                          {reg.razorpay_payment_id}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                          reg.status === 'CONFIRMED'
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            : 'bg-slate-100 text-slate-600 border border-slate-200'
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
                    <td className="py-3 px-4">
                      <button
                        onClick={() => handleSyncRegistration(reg.registration_id)}
                        disabled={syncingId === reg.registration_id}
                        className="px-2.5 py-1 bg-slate-100 hover:bg-amber-500 hover:text-slate-950 text-slate-700 font-bold rounded-lg text-[11px] uppercase transition border border-slate-200 shadow-sm"
                        title="Sync to Zoho CRM"
                      >
                        {syncingId === reg.registration_id ? '...' : 'Sync'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {total > pageSize && (
          <div className="flex items-center justify-between px-6 py-4 bg-slate-50 border-t border-slate-200">
            <span className="text-xs text-slate-600">
              Showing <strong className="text-slate-900">{(page - 1) * pageSize + 1}</strong> to{' '}
              <strong className="text-slate-900">{Math.min(page * pageSize, total)}</strong> of{' '}
              <strong className="text-slate-900">{total}</strong> registrations
            </span>

            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 bg-white hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed text-slate-700 rounded-lg text-xs font-bold transition border border-slate-200"
              >
                Previous
              </button>
              <span className="text-xs text-slate-600 px-2 font-mono">
                {page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="px-3 py-1.5 bg-white hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed text-slate-700 rounded-lg text-xs font-bold transition border border-slate-200"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
