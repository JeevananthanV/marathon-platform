import React, { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { AdminLeadItem, LeadStatus } from '@/types';

interface AdminLeadsViewProps {
  adminKey: string;
}

const STATUS_COLORS: Record<LeadStatus, { bg: string; text: string; border: string }> = {
  NEW: { bg: 'bg-blue-50', text: 'text-blue-800', border: 'border-blue-200' },
  CONTACTED: { bg: 'bg-indigo-50', text: 'text-indigo-800', border: 'border-indigo-200' },
  REGISTERED: { bg: 'bg-cyan-50', text: 'text-cyan-800', border: 'border-cyan-200' },
  PAYMENT_PENDING: { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200' },
  CONVERTED: { bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200' },
  LOST: { bg: 'bg-red-50', text: 'text-red-800', border: 'border-red-200' },
};

const ALL_STATUSES: LeadStatus[] = ['NEW', 'CONTACTED', 'REGISTERED', 'PAYMENT_PENDING', 'CONVERTED', 'LOST'];

export const AdminLeadsView: React.FC<AdminLeadsViewProps> = ({ adminKey }) => {
  const [leads, setLeads] = useState<AdminLeadItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination
  const [search, setSearch] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [page, setPage] = useState<number>(1);
  const pageSize = 20;

  // Updating lead status indicator
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getAdminLeads(adminKey, {
        search: search.trim() || undefined,
        status: selectedStatus !== 'ALL' ? selectedStatus : undefined,
        page,
        page_size: pageSize,
      });
      setLeads(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch leads');
    } finally {
      setLoading(false);
    }
  }, [adminKey, search, selectedStatus, page]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  const handleStatusChange = async (leadId: string, newStatus: LeadStatus) => {
    setUpdatingId(leadId);
    try {
      const updated = await api.updateLeadStatus(adminKey, leadId, newStatus);
      setLeads((prev) =>
        prev.map((item) => (item.id === leadId ? { ...item, lead_status: updated.lead_status } : item))
      );
    } catch (err: any) {
      alert(`Error updating lead status: ${err.message}`);
    } finally {
      setUpdatingId(null);
    }
  };

  const exportUrl = api.getExportLeadsUrl(adminKey);
  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Header & Export */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-slate-900 uppercase tracking-wider">
            Lead Management
          </h2>
          <p className="text-sm text-slate-600">
            Track inquiries, update lead pipeline statuses, and monitor acquisition channels with Zoho CRM.
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
          Export Leads CSV
        </a>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search Box */}
          <div className="relative col-span-2">
            <input
              type="text"
              placeholder="Search by runner name, email, or phone number..."
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

          {/* Quick Refresh Button */}
          <div className="flex justify-end items-center">
            <button
              onClick={fetchLeads}
              className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-bold uppercase tracking-wider transition border border-slate-200 w-full md:w-auto"
            >
              Refresh
            </button>
          </div>
        </div>

        {/* Status Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider mr-2">
            Filter Status:
          </span>
          <button
            onClick={() => {
              setSelectedStatus('ALL');
              setPage(1);
            }}
            className={`px-3 py-1 rounded-lg text-xs font-bold uppercase transition ${
              selectedStatus === 'ALL'
                ? 'bg-amber-500 text-slate-950 shadow-sm'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200'
            }`}
          >
            All ({total})
          </button>
          {ALL_STATUSES.map((st) => (
            <button
              key={st}
              onClick={() => {
                setSelectedStatus(st);
                setPage(1);
              }}
              className={`px-3 py-1 rounded-lg text-xs font-bold uppercase transition ${
                selectedStatus === st
                  ? 'bg-amber-500 text-slate-950 shadow-sm'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Leads Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="text-center py-16 text-slate-500 text-sm">
            <svg className="w-8 h-8 animate-spin mx-auto text-amber-500 mb-3" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Loading participant leads...
          </div>
        ) : leads.length === 0 ? (
          <div className="text-center py-16 text-slate-400 text-sm">
            No leads found matching current search or filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="text-[11px] uppercase tracking-wider text-slate-700 bg-slate-100 border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Lead Name</th>
                  <th className="py-3 px-4">Contact Details</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Marketing / UTM</th>
                  <th className="py-3 px-4">Pipeline Status</th>
                  <th className="py-3 px-4">Payment</th>
                  <th className="py-3 px-4">Zoho Sync</th>
                  <th className="py-3 px-4">Registered</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {leads.map((lead) => {
                  const style = STATUS_COLORS[lead.lead_status] || STATUS_COLORS.NEW;
                  const isUpdating = updatingId === lead.id;

                  return (
                    <tr key={lead.id} className="hover:bg-slate-50 transition">
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-900 text-sm">{lead.name}</div>
                        <div className="text-[11px] text-slate-500">
                          {lead.city}, {lead.state}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-slate-800 font-mono">{lead.email}</div>
                        <div className="text-slate-500 font-mono text-[11px]">{lead.phone}</div>
                      </td>
                      <td className="py-3 px-4">
                        {lead.category_code ? (
                          <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-bold border border-slate-200">
                            {lead.category_code}
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {lead.utm_source ? (
                          <div>
                            <span className="inline-block px-2 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-200 font-bold uppercase text-[10px]">
                              {lead.utm_source}
                            </span>
                            {lead.utm_campaign && (
                              <div className="text-[10px] text-slate-500 truncate max-w-[120px] mt-0.5">
                                {lead.utm_campaign}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400 text-[11px]">Direct</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {/* Interactive Inline Status Dropdown */}
                        <div className="relative inline-block">
                          <select
                            disabled={isUpdating}
                            value={lead.lead_status}
                            onChange={(e) => handleStatusChange(lead.id, e.target.value as LeadStatus)}
                            className={`appearance-none cursor-pointer text-xs font-bold uppercase px-3 py-1 pr-7 rounded-lg border focus:outline-none transition ${style.bg} ${style.text} ${style.border}`}
                          >
                            {ALL_STATUSES.map((st) => (
                              <option key={st} value={st} className="bg-white text-slate-900 font-medium">
                                {st}
                              </option>
                            ))}
                          </select>
                          <svg
                            className={`w-3 h-3 absolute right-2 top-2 pointer-events-none ${style.text}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                            lead.payment_status === 'SUCCESS'
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                              : 'bg-slate-100 text-slate-600 border border-slate-200'
                          }`}
                        >
                          {lead.payment_status}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                            lead.zoho_sync_status === 'SYNCED'
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                              : lead.zoho_sync_status === 'FAILED'
                              ? 'bg-red-100 text-red-800 border border-red-200'
                              : 'bg-slate-100 text-slate-600 border border-slate-200'
                          }`}
                        >
                          {lead.zoho_sync_status || 'PENDING'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {lead.created_at ? new Date(lead.created_at).toLocaleDateString('en-IN') : '—'}
                      </td>
                    </tr>
                  );
                })}
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
              <strong className="text-slate-900">{total}</strong> leads
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
