'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  Clock,
  Globe,
  Headphones,
  PhoneCall,
  RefreshCw,
  Search,
  ShieldCheck,
  User,
} from 'lucide-react';

export interface EscalationItem {
  id: number;
  reference_id: string;
  user_id: string;
  name: string | null;
  language: string | null;
  reason: string;
  summary: string;
  what_was_checked: string | null;
  urgency: 'LOW' | 'MEDIUM' | 'HIGH';
  preferred_follow_up: string | null;
  status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED';
  created_at: string;
  updated_at: string;
}

export function HumanHelpDashboard() {
  const [escalations, setEscalations] = useState<EscalationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const fetchEscalations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const url = activeTab === 'ALL' ? '/api/escalations' : `/api/escalations?status=${activeTab}`;
      const res = await fetch(url);
      const data = await res.json();

      if (data.success && Array.isArray(data.escalations)) {
        setEscalations(data.escalations);
      } else {
        setError(data.error || 'Failed to load human-help requests.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error loading escalations.');
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchEscalations();
  }, [activeTab, fetchEscalations]);

  const handleStatusChange = async (
    refId: string,
    newStatus: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED'
  ) => {
    try {
      setUpdatingId(refId);
      const res = await fetch(`/api/escalations/${refId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      const data = await res.json();
      if (data.success && data.escalation) {
        setEscalations((prev) =>
          prev.map((item) => (item.reference_id === refId ? data.escalation : item))
        );
      } else {
        alert(`Failed to update status: ${data.message || data.error}`);
      }
    } catch (err) {
      alert(`Error updating status: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setUpdatingId(null);
    }
  };

  const filteredEscalations = escalations.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.reference_id.toLowerCase().includes(q) ||
      item.reason.toLowerCase().includes(q) ||
      item.summary.toLowerCase().includes(q) ||
      (item.name && item.name.toLowerCase().includes(q)) ||
      (item.language && item.language.toLowerCase().includes(q)) ||
      item.user_id.toLowerCase().includes(q)
    );
  });

  const counts = {
    total: escalations.length,
    open: escalations.filter((i) => i.status === 'OPEN').length,
    in_progress: escalations.filter((i) => i.status === 'IN_PROGRESS').length,
    resolved: escalations.filter((i) => i.status === 'RESOLVED').length,
  };

  return (
    <div className="mx-auto w-full max-w-7xl px-3 py-6 sm:px-6 lg:px-8">
      {/* Header Banner */}
      <div className="mb-6 rounded-2xl border border-amber-500/20 bg-gradient-to-r from-amber-500/10 via-orange-500/5 to-indigo-500/10 p-5 shadow-lg backdrop-blur-md">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-tr from-amber-500 to-orange-600 shadow-md shadow-amber-500/30">
              <Headphones className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-foreground text-2xl font-bold tracking-tight">
                Bharat Voice AI - Human Help
              </h1>
              <p className="text-muted-foreground text-xs sm:text-sm">
                Human Assistance Escalation Dashboard & Case Management
              </p>
            </div>
          </div>

          <button
            onClick={fetchEscalations}
            disabled={loading}
            className="inline-flex items-center justify-center rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm font-semibold text-amber-600 transition-all hover:bg-amber-500/20 disabled:opacity-50 dark:text-amber-300"
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh Queue
          </button>
        </div>

        {/* Metrics Row */}
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="border-border/50 bg-background/60 rounded-xl border p-3 backdrop-blur-sm">
            <div className="text-muted-foreground text-xs font-medium">Total Requests</div>
            <div className="text-foreground mt-1 text-2xl font-bold">{counts.total}</div>
          </div>
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 backdrop-blur-sm">
            <div className="text-xs font-semibold text-amber-700 dark:text-amber-300">
              Open Requests
            </div>
            <div className="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">
              {counts.open}
            </div>
          </div>
          <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-3 backdrop-blur-sm">
            <div className="text-xs font-semibold text-blue-700 dark:text-blue-300">
              In Progress
            </div>
            <div className="mt-1 text-2xl font-bold text-blue-600 dark:text-blue-400">
              {counts.in_progress}
            </div>
          </div>
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 backdrop-blur-sm">
            <div className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">
              Resolved
            </div>
            <div className="mt-1 text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              {counts.resolved}
            </div>
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* Status Filter Tabs */}
        <div className="border-border bg-muted/40 flex flex-wrap items-center gap-1.5 rounded-xl border p-1.5 backdrop-blur-md">
          {['ALL', 'OPEN', 'IN_PROGRESS', 'RESOLVED'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                activeTab === tab
                  ? 'bg-background text-foreground border-border border shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab === 'ALL'
                ? 'All Requests'
                : tab === 'OPEN'
                  ? 'Open'
                  : tab === 'IN_PROGRESS'
                    ? 'In Progress'
                    : 'Resolved'}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-72">
          <Search className="text-muted-foreground absolute top-2.5 left-3 h-4 w-4" />
          <input
            type="text"
            placeholder="Search reference ID, reason, caller..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="border-border bg-background text-foreground placeholder:text-muted-foreground w-full rounded-xl border px-3 py-2 pl-9 text-xs focus:border-amber-500 focus:ring-1 focus:ring-amber-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="border-border bg-card flex h-64 items-center justify-center rounded-2xl border">
          <div className="flex flex-col items-center space-y-3">
            <RefreshCw className="h-8 w-8 animate-spin text-amber-500" />
            <p className="text-muted-foreground text-sm font-medium">
              Loading escalation requests...
            </p>
          </div>
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-center text-rose-600 dark:text-rose-400">
          <AlertCircle className="mx-auto mb-2 h-8 w-8" />
          <p className="font-semibold">{error}</p>
          <button
            onClick={fetchEscalations}
            className="mt-3 rounded-lg border border-rose-500/40 bg-rose-500/20 px-4 py-1.5 text-xs font-semibold transition-colors hover:bg-rose-500/30"
          >
            Try Again
          </button>
        </div>
      ) : filteredEscalations.length === 0 ? (
        <div className="border-border bg-card/50 flex h-64 flex-col items-center justify-center rounded-2xl border border-dashed p-6 text-center">
          <ShieldCheck className="text-muted-foreground/60 mb-2 h-10 w-10" />
          <h3 className="text-foreground text-base font-bold">No Escalation Requests Found</h3>
          <p className="text-muted-foreground mt-1 text-xs">
            {searchQuery
              ? 'No requests match your current search query.'
              : 'There are currently no human-help requests in this queue.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {filteredEscalations.map((item) => (
            <div
              key={item.reference_id}
              className="border-border/80 bg-card flex flex-col justify-between rounded-2xl border p-5 shadow-sm transition-all hover:border-amber-500/40 hover:shadow-md"
            >
              {/* Header: Ref ID, Urgency & Status Badge */}
              <div>
                <div className="border-border/40 flex items-start justify-between gap-2 border-b pb-3">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-base font-bold tracking-tight text-amber-600 dark:text-amber-400">
                        {item.reference_id}
                      </span>
                      {/* Urgency Badge */}
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase ${
                          item.urgency === 'HIGH'
                            ? 'border border-rose-500/30 bg-rose-500/15 text-rose-600 dark:text-rose-400'
                            : item.urgency === 'MEDIUM'
                              ? 'border border-amber-500/30 bg-amber-500/15 text-amber-600 dark:text-amber-400'
                              : 'border border-slate-500/30 bg-slate-500/15 text-slate-600 dark:text-slate-400'
                        }`}
                      >
                        {item.urgency} Urgency
                      </span>
                    </div>
                    <div className="text-foreground mt-1 text-xs font-semibold">
                      Reason:{' '}
                      <span className="text-muted-foreground font-normal">{item.reason}</span>
                    </div>
                  </div>

                  {/* Status Dropdown */}
                  <div className="relative">
                    <select
                      value={item.status}
                      disabled={updatingId === item.reference_id}
                      onChange={(e) =>
                        handleStatusChange(
                          item.reference_id,
                          e.target.value as 'OPEN' | 'IN_PROGRESS' | 'RESOLVED'
                        )
                      }
                      className={`cursor-pointer rounded-xl border px-3 py-1.5 text-xs font-bold transition-all focus:outline-none ${
                        item.status === 'OPEN'
                          ? 'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400'
                          : item.status === 'IN_PROGRESS'
                            ? 'border-blue-500/40 bg-blue-500/10 text-blue-600 dark:text-blue-400'
                            : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                      }`}
                    >
                      <option value="OPEN" className="bg-background text-foreground">
                        OPEN
                      </option>
                      <option value="IN_PROGRESS" className="bg-background text-foreground">
                        IN_PROGRESS
                      </option>
                      <option value="RESOLVED" className="bg-background text-foreground">
                        RESOLVED
                      </option>
                    </select>
                  </div>
                </div>

                {/* Details Section */}
                <div className="mt-4 space-y-2.5 text-xs">
                  {/* Caller Info */}
                  <div className="bg-muted/30 grid grid-cols-2 gap-2 rounded-xl p-2.5">
                    <div className="text-muted-foreground flex items-center space-x-1.5">
                      <User className="h-3.5 w-3.5 text-amber-500" />
                      <span>Caller Name:</span>
                      <strong className="text-foreground font-semibold">
                        {item.name || 'Not provided'}
                      </strong>
                    </div>
                    <div className="text-muted-foreground flex items-center space-x-1.5">
                      <Globe className="h-3.5 w-3.5 text-amber-500" />
                      <span>Language:</span>
                      <strong className="text-foreground font-semibold">
                        {item.language || 'Gujarati / Hindi'}
                      </strong>
                    </div>
                  </div>

                  {/* Summary */}
                  <div>
                    <div className="text-foreground font-semibold">Summary:</div>
                    <p className="border-border/40 bg-background/50 text-muted-foreground mt-0.5 rounded-lg border p-2 leading-relaxed">
                      {item.summary}
                    </p>
                  </div>

                  {/* What Was Checked */}
                  {item.what_was_checked && (
                    <div>
                      <div className="text-foreground font-semibold">What Was Checked:</div>
                      <p className="text-muted-foreground mt-0.5">{item.what_was_checked}</p>
                    </div>
                  )}

                  {/* Preferred Follow Up */}
                  <div className="text-muted-foreground flex items-center space-x-2">
                    <PhoneCall className="h-3.5 w-3.5 text-emerald-500" />
                    <span>Preferred Follow-up:</span>
                    <span className="text-foreground font-medium capitalize">
                      {item.preferred_follow_up || 'phone'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Timestamps Footer */}
              <div className="border-border/40 text-muted-foreground mt-4 flex items-center justify-between border-t pt-3 text-[11px]">
                <div className="flex items-center space-x-1">
                  <Clock className="h-3 w-3" />
                  <span>Created: {new Date(item.created_at).toLocaleString()}</span>
                </div>
                <span>Updated: {new Date(item.updated_at).toLocaleTimeString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
