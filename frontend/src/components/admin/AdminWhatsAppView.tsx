import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { WhatsAppStatsSummary, WhatsAppMessageItem, WhatsAppMessageListResponse } from '@/types';

interface AdminWhatsAppViewProps {
  adminKey: string;
}

export const AdminWhatsAppView: React.FC<AdminWhatsAppViewProps> = ({ adminKey }) => {
  const [stats, setStats] = useState<WhatsAppStatsSummary | null>(null);
  const [messageData, setMessageData] = useState<WhatsAppMessageListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [batchRetrying, setBatchRetrying] = useState(false);
  const [triggeringReminder, setTriggeringReminder] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsRes, messagesRes] = await Promise.all([
        api.getWhatsAppStats(adminKey),
        api.getWhatsAppMessages(adminKey, {
          phone_number: searchTerm ? searchTerm : undefined,
          message_type: selectedType ? selectedType : undefined,
          status: selectedStatus ? selectedStatus : undefined,
          page,
          page_size: pageSize,
        }),
      ]);
      setStats(statsRes);
      setMessageData(messagesRes);
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Failed to load WhatsApp communication data.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [adminKey, page, selectedType, selectedStatus]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  const handleRetrySingle = async (messageId: string) => {
    try {
      setRetryingId(messageId);
      const res = await api.retryWhatsAppMessage(adminKey, messageId);
      if (res.status === 'SUCCESS') {
        setFeedback({ type: 'success', message: `Message ${messageId.slice(0, 8)} successfully dispatched!` });
      } else {
        setFeedback({ type: 'error', message: res.error || 'Retry attempt failed.' });
      }
      await loadData();
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Failed to retry WhatsApp message.' });
    } finally {
      setRetryingId(null);
    }
  };

  const handleBatchRetry = async () => {
    try {
      setBatchRetrying(true);
      const res = await api.retryAllFailedWhatsApp(adminKey, 50);
      setFeedback({
        type: 'success',
        message: `Batch retry completed: ${res.successful} successful, ${res.failed} failed out of ${res.total_processed} items.`,
      });
      await loadData();
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Batch retry failed.' });
    } finally {
      setBatchRetrying(false);
    }
  };

  const handleTriggerDueReminders = async (type?: string) => {
    try {
      setTriggeringReminder(true);
      const res = await api.triggerProcessDueReminders(adminKey, type);
      setFeedback({
        type: 'success',
        message: `Reminder processor executed: ${res.sent_count} sent, ${res.skipped_count} already delivered, ${res.failed_count} failed.`,
      });
      await loadData();
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Failed to trigger due reminders.' });
    } finally {
      setTriggeringReminder(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'READ':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <svg className="w-3 h-3 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            Read
          </span>
        );
      case 'DELIVERED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-100 text-cyan-800 border border-cyan-200">
            <svg className="w-3 h-3 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Delivered
          </span>
        );
      case 'SENT':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
            <svg className="w-3 h-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            Sent
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            <svg className="w-3 h-3 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <svg className="w-3 h-3 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Pending
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-slate-200 p-6 rounded-2xl shadow-md">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-xl">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-black text-slate-900 uppercase tracking-wider">WhatsApp Automation & Communication Ledger</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Participant confirmations, BIB alerts, scheduled reminders, and webhook delivery tracking.
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {stats?.provider_health && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 rounded-lg text-xs font-medium text-slate-700 border border-slate-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Mode: <strong className="uppercase text-emerald-700">{stats.provider_health.mode}</strong>
            </div>
          )}

          <button
            onClick={() => handleBatchRetry()}
            disabled={batchRetrying || (stats?.failed_count ?? 0) === 0}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold text-amber-900 bg-amber-100 hover:bg-amber-200 border border-amber-300 rounded-lg transition disabled:opacity-50"
          >
            <svg className={`w-3.5 h-3.5 ${batchRetrying ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {batchRetrying ? 'Retrying...' : 'Retry All Failed'}
          </button>

          <button
            onClick={() => loadData()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-lg transition"
          >
            <svg className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Feedback Toast */}
      {feedback && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between gap-3 ${
            feedback.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          <div className="flex items-center gap-2 text-xs font-medium">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{feedback.message}</span>
          </div>
          <button
            onClick={() => setFeedback(null)}
            className="text-[10px] uppercase tracking-wider font-bold hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Statistics Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Total Ledger</div>
          <div className="text-2xl font-black text-slate-900 mt-1">{stats?.total_messages ?? 0}</div>
          <div className="text-[10px] text-slate-400 mt-1">All dispatches</div>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm">
          <div className="text-[10px] font-bold text-blue-700 uppercase tracking-wider">Sent</div>
          <div className="text-2xl font-black text-blue-600 mt-1">{stats?.sent_count ?? 0}</div>
          <div className="text-[10px] text-blue-500 mt-1">In transit</div>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm">
          <div className="text-[10px] font-bold text-cyan-700 uppercase tracking-wider">Delivered</div>
          <div className="text-2xl font-black text-cyan-600 mt-1">{stats?.delivered_count ?? 0}</div>
          <div className="text-[10px] text-cyan-500 mt-1">Device reached</div>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm">
          <div className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">Read Receipts</div>
          <div className="text-2xl font-black text-emerald-600 mt-1">{stats?.read_count ?? 0}</div>
          <div className="text-[10px] text-emerald-500 mt-1">Seen by runner</div>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm">
          <div className="text-[10px] font-bold text-rose-700 uppercase tracking-wider">Failed</div>
          <div className="text-2xl font-black text-rose-600 mt-1">{stats?.failed_count ?? 0}</div>
          <div className="text-[10px] text-rose-500 mt-1">Retry eligible</div>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm">
          <div className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">Pending</div>
          <div className="text-2xl font-black text-amber-600 mt-1">{stats?.pending_count ?? 0}</div>
          <div className="text-[10px] text-amber-500 mt-1">Queued</div>
        </div>
      </div>

      {/* Reminder Scheduler Quick Action Toolbar */}
      <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 text-slate-900 p-5 rounded-2xl shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-emerald-100 text-emerald-800 border border-emerald-200 rounded-xl">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
          </div>
          <div>
            <h3 className="font-bold text-sm text-slate-900 uppercase tracking-wider">Marathon Reminder Dispatch Engine</h3>
            <p className="text-xs text-slate-600">
              Evaluates confirmed runners with WhatsApp consent and dispatches scheduled reminders idempotently.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => handleTriggerDueReminders('REMINDER_7_DAYS')}
            disabled={triggeringReminder}
            className="px-3 py-1.5 text-xs font-bold bg-white hover:bg-slate-50 text-emerald-800 rounded-lg border border-emerald-300 transition shadow-sm"
          >
            7-Day Alerts
          </button>
          <button
            onClick={() => handleTriggerDueReminders('REMINDER_3_DAYS')}
            disabled={triggeringReminder}
            className="px-3 py-1.5 text-xs font-bold bg-white hover:bg-slate-50 text-emerald-800 rounded-lg border border-emerald-300 transition shadow-sm"
          >
            3-Day Expo
          </button>
          <button
            onClick={() => handleTriggerDueReminders('REMINDER_1_DAY')}
            disabled={triggeringReminder}
            className="px-3 py-1.5 text-xs font-bold bg-white hover:bg-slate-50 text-emerald-800 rounded-lg border border-emerald-300 transition shadow-sm"
          >
            1-Day Eve
          </button>
          <button
            onClick={() => handleTriggerDueReminders('REMINDER_RACE_DAY')}
            disabled={triggeringReminder}
            className="px-3 py-1.5 text-xs font-bold bg-white hover:bg-slate-50 text-emerald-800 rounded-lg border border-emerald-300 transition shadow-sm"
          >
            Race Morning
          </button>
          <button
            onClick={() => handleTriggerDueReminders()}
            disabled={triggeringReminder}
            className="px-4 py-1.5 text-xs font-black uppercase tracking-wider bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition shadow-md"
          >
            {triggeringReminder ? 'Processing...' : 'Run All Due'}
          </button>
        </div>
      </div>

      {/* Filters Toolbar */}
      <div className="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 w-full md:w-auto">
          <div className="relative w-full md:w-72">
            <svg className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search phone number..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400 focus:ring-1 focus:ring-amber-500 focus:outline-none shadow-sm"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-slate-950 bg-amber-500 hover:bg-amber-400 rounded-xl transition shadow-sm"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Type:</span>
            <select
              value={selectedType}
              onChange={(e) => {
                setSelectedType(e.target.value);
                setPage(1);
              }}
              className="text-xs bg-white border border-slate-300 text-slate-800 rounded-xl px-2.5 py-1.5 focus:ring-1 focus:ring-amber-500 focus:outline-none shadow-sm"
            >
              <option value="">All Message Types</option>
              <option value="REGISTRATION_CONFIRMATION">Registration Initiation</option>
              <option value="PAYMENT_CONFIRMATION">Payment & Digital Pass</option>
              <option value="REMINDER_7_DAYS">7 Days Reminder</option>
              <option value="REMINDER_3_DAYS">3 Days Reminder</option>
              <option value="REMINDER_1_DAY">1 Day Reminder</option>
              <option value="REMINDER_RACE_DAY">Race Day Morning</option>
              <option value="POST_EVENT_THANKS">Post-Event Thank You</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setPage(1);
              }}
              className="text-xs bg-white border border-slate-300 text-slate-800 rounded-xl px-2.5 py-1.5 focus:ring-1 focus:ring-amber-500 focus:outline-none shadow-sm"
            >
              <option value="">All Statuses</option>
              <option value="SENT">Sent</option>
              <option value="DELIVERED">Delivered</option>
              <option value="READ">Read</option>
              <option value="FAILED">Failed</option>
              <option value="PENDING">Pending</option>
            </select>
          </div>
        </div>
      </div>

      {/* Messages Ledger Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-100 text-slate-700 uppercase font-black tracking-wider text-[10px] border-b border-slate-200">
              <tr>
                <th className="px-4 py-3.5">Recipient & Time</th>
                <th className="px-4 py-3.5">Message Type</th>
                <th className="px-4 py-3.5">Content Preview</th>
                <th className="px-4 py-3.5">Delivery Status</th>
                <th className="px-4 py-3.5">Provider ID</th>
                <th className="px-4 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-16 text-slate-500">
                    <svg className="w-8 h-8 animate-spin mx-auto text-amber-500 mb-2" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Loading WhatsApp communication ledger...
                  </td>
                </tr>
              ) : !messageData?.items?.length ? (
                <tr>
                  <td colSpan={6} className="text-center py-16 text-slate-400">
                    No WhatsApp messages found matching the selected criteria.
                  </td>
                </tr>
              ) : (
                messageData.items.map((msg: WhatsAppMessageItem) => (
                  <tr key={msg.id} className="hover:bg-slate-50 transition">
                    <td className="px-4 py-3.5">
                      <div className="font-bold text-slate-900">{msg.phone_number}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {new Date(msg.created_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="font-semibold text-slate-800">{msg.message_type}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{msg.template_name}</div>
                    </td>
                    <td className="px-4 py-3.5 max-w-xs truncate text-slate-600">
                      {msg.message_content || 'Template parameter payload'}
                    </td>
                    <td className="px-4 py-3.5">
                      {getStatusBadge(msg.status)}
                      {msg.error_message && (
                        <div className="text-[10px] text-rose-600 max-w-xs truncate mt-1" title={msg.error_message}>
                          {msg.error_message}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-[10px] text-slate-500">
                      {msg.provider_message_id ? msg.provider_message_id.slice(0, 22) + '...' : '—'}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      {msg.status === 'FAILED' ? (
                        <button
                          onClick={() => handleRetrySingle(msg.id)}
                          disabled={retryingId === msg.id}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-bold text-amber-900 bg-amber-100 hover:bg-amber-200 border border-amber-300 rounded-lg transition disabled:opacity-50"
                        >
                          <svg className={`w-3 h-3 ${retryingId === msg.id ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                          {retryingId === msg.id ? 'Retrying...' : 'Retry'}
                        </button>
                      ) : (
                        <span className="text-[10px] text-slate-400 font-mono">Retries: {msg.retry_count}</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {messageData && messageData.total > pageSize && (
          <div className="p-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600 bg-slate-50">
            <div>
              Showing {Math.min((page - 1) * pageSize + 1, messageData.total)} to{' '}
              {Math.min(page * pageSize, messageData.total)} of {messageData.total} messages
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 bg-white border border-slate-200 text-slate-700 rounded-lg hover:bg-slate-100 disabled:opacity-50"
              >
                Previous
              </button>
              <span className="px-2 font-bold text-slate-900">Page {page}</span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page * pageSize >= messageData.total}
                className="px-3 py-1 bg-white border border-slate-200 text-slate-700 rounded-lg hover:bg-slate-100 disabled:opacity-50"
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
