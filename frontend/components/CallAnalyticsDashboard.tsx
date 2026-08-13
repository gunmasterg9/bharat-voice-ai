'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertCircle,
  BarChart3,
  CheckCircle2,
  Clock,
  Globe,
  Phone,
  PhoneCall,
  RefreshCw,
  Shield,
  Smartphone,
  Sparkles,
  TrendingUp,
  XCircle,
} from 'lucide-react';

interface AnalyticsSummary {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
}

interface CallRecord {
  call_id: string;
  user_id: string | null;
  channel: 'BROWSER' | 'SIP' | string;
  language: string | null;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  outcome: 'SUCCESS' | 'FAILED' | 'INCOMPLETE' | 'ERROR' | string;
  success_reason: string | null;
  failure_reason: string | null;
  tool_used: string | null;
  escalation_created: number | boolean;
}

export function CallAnalyticsDashboard() {
  const [summary, setSummary] = useState<AnalyticsSummary>({
    total_calls: 0,
    successful_calls: 0,
    failed_calls: 0,
  });
  const [calls, setCalls] = useState<CallRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchAnalytics = useCallback(async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      const [sumRes, callsRes] = await Promise.all([
        fetch('/api/analytics/summary', { cache: 'no-store' }),
        fetch('/api/analytics/calls?limit=50', { cache: 'no-store' }),
      ]);

      if (sumRes.ok) {
        const sumData = await sumRes.json();
        if (sumData.success) {
          setSummary({
            total_calls: sumData.total_calls || 0,
            successful_calls: sumData.successful_calls || 0,
            failed_calls: sumData.failed_calls || 0,
          });
        }
      }

      if (callsRes.ok) {
        const callsData = await callsRes.json();
        if (callsData.success && Array.isArray(callsData.calls)) {
          setCalls(callsData.calls);
        }
      }

      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to load call analytics:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalytics();
    // Auto-refresh every 5 seconds
    const interval = setInterval(() => {
      fetchAnalytics();
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchAnalytics]);

  const successRate =
    summary.total_calls > 0
      ? ((summary.successful_calls / summary.total_calls) * 100).toFixed(1)
      : '0.0';

  const formatDuration = (seconds: number | null) => {
    if (seconds === null || seconds === undefined || seconds < 0) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatTime = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      {/* Header Section */}
      <div className="border-border/40 flex flex-col gap-4 border-b pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-foreground text-2xl font-bold tracking-tight sm:text-3xl">
              Bharat Voice AI — Call Analytics
            </h1>
            <span className="inline-flex items-center rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-600 dark:text-amber-400">
              <Sparkles className="mr-1 h-3 w-3" />
              Day 8
            </span>
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            Voice Agent Performance Dashboard — Real operational call metrics from SQLite
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-muted-foreground hidden text-xs sm:block">
            {lastUpdated && `Updated: ${lastUpdated.toLocaleTimeString()}`}
          </div>
          <button
            onClick={() => fetchAnalytics(true)}
            disabled={refreshing}
            className="border-border bg-background text-foreground hover:bg-accent inline-flex items-center space-x-1.5 rounded-xl border px-3 py-2 text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh Data</span>
          </button>
        </div>
      </div>

      {/* 3 Metric Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:gap-6">
        {/* TOTAL CALLS Card */}
        <div className="border-border bg-card relative overflow-hidden rounded-2xl border p-6 shadow-sm transition-all hover:shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground text-xs font-bold tracking-wider uppercase">
              TOTAL CALLS
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
              <PhoneCall className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <div className="text-foreground text-4xl font-extrabold tracking-tight">
              {loading ? '...' : summary.total_calls}
            </div>
            <span className="text-muted-foreground inline-flex items-center text-xs font-medium">
              <Activity className="mr-1 h-3.5 w-3.5 text-indigo-500" />
              All Channels
            </span>
          </div>
          <div className="text-muted-foreground mt-3 text-xs">
            Actual voice conversations recorded in SQLite
          </div>
        </div>

        {/* SUCCESSFUL CALLS Card */}
        <div className="relative overflow-hidden rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-6 shadow-sm transition-all hover:shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold tracking-wider text-emerald-600 uppercase dark:text-emerald-400">
              SUCCESSFUL CALLS
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <div className="text-4xl font-extrabold tracking-tight text-emerald-600 dark:text-emerald-400">
              {loading ? '...' : summary.successful_calls}
            </div>
            <span className="inline-flex items-center rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              <TrendingUp className="mr-1 h-3 w-3" />
              {successRate}% Success Rate
            </span>
          </div>
          <div className="mt-3 text-xs text-emerald-600/80 dark:text-emerald-400/80">
            Primary user intent completed without failure
          </div>
        </div>

        {/* FAILED CALLS Card */}
        <div className="relative overflow-hidden rounded-2xl border border-rose-500/30 bg-rose-500/5 p-6 shadow-sm transition-all hover:shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold tracking-wider text-rose-600 uppercase dark:text-rose-400">
              FAILED CALLS
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-500/20 text-rose-600 dark:text-rose-400">
              <XCircle className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <div className="text-4xl font-extrabold tracking-tight text-rose-600 dark:text-rose-400">
              {loading ? '...' : summary.failed_calls}
            </div>
            <span className="inline-flex items-center text-xs font-medium text-rose-600/80 dark:text-rose-400/80">
              <AlertCircle className="mr-1 h-3.5 w-3.5 text-rose-500" />
              Incomplete & Failed
            </span>
          </div>
          <div className="mt-3 text-xs text-rose-600/80 dark:text-rose-400/80">
            Tool failures, unexpected hangups or incomplete tasks
          </div>
        </div>
      </div>

      {/* Recent Call History Section */}
      <div className="border-border bg-card overflow-hidden rounded-2xl border shadow-sm">
        <div className="border-border/40 flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center space-x-2">
            <BarChart3 className="h-5 w-5 text-amber-500" />
            <h2 className="text-foreground text-lg font-bold">Recent Call History</h2>
          </div>
          <div className="text-muted-foreground flex items-center space-x-1.5 text-xs">
            <Shield className="h-3.5 w-3.5 text-emerald-500" />
            <span>Privacy Filtered Operational Logs</span>
          </div>
        </div>

        {loading ? (
          <div className="text-muted-foreground p-8 text-center text-sm">
            Loading call records...
          </div>
        ) : calls.length === 0 ? (
          <div className="text-muted-foreground p-8 text-center text-sm">
            No calls recorded yet. Make a live Browser or SIP call to populate real metrics!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-border text-muted-foreground border-b text-[10px] font-bold tracking-wider uppercase">
                <tr>
                  <th className="px-6 py-3">Time</th>
                  <th className="px-6 py-3">Call ID</th>
                  <th className="px-6 py-3">Channel</th>
                  <th className="px-6 py-3">Language</th>
                  <th className="px-6 py-3">Duration</th>
                  <th className="px-6 py-3">Outcome</th>
                  <th className="px-6 py-3">Tool / Details</th>
                </tr>
              </thead>
              <tbody className="divide-border/40 divide-y">
                {calls.map((call) => {
                  const isSuccess = call.outcome === 'SUCCESS';
                  const isFailed = call.outcome === 'FAILED' || call.outcome === 'ERROR';
                  const isSIP = call.channel === 'SIP';

                  return (
                    <tr key={call.call_id} className="hover:bg-muted/30 transition-colors">
                      <td className="text-foreground px-6 py-4 font-mono font-medium whitespace-nowrap">
                        {formatTime(call.started_at)}
                      </td>
                      <td className="text-muted-foreground max-w-[140px] truncate px-6 py-4 font-mono">
                        {call.call_id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${
                            isSIP
                              ? 'border-purple-500/20 bg-purple-500/10 text-purple-600 dark:text-purple-400'
                              : 'border-blue-500/20 bg-blue-500/10 text-blue-600 dark:text-blue-400'
                          }`}
                        >
                          {isSIP ? (
                            <Phone className="mr-1 h-3 w-3" />
                          ) : (
                            <Smartphone className="mr-1 h-3 w-3" />
                          )}
                          {call.channel}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-foreground inline-flex items-center font-medium">
                          <Globe className="text-muted-foreground mr-1.5 h-3.5 w-3.5" />
                          {call.language || 'English'}
                        </span>
                      </td>
                      <td className="text-foreground px-6 py-4 font-mono whitespace-nowrap">
                        <div className="flex items-center space-x-1">
                          <Clock className="text-muted-foreground h-3 w-3" />
                          <span>{formatDuration(call.duration_seconds)}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${
                            isSuccess
                              ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                              : isFailed
                                ? 'border-rose-500/20 bg-rose-500/10 text-rose-600 dark:text-rose-400'
                                : 'border-amber-500/20 bg-amber-500/10 text-amber-600 dark:text-amber-400'
                          }`}
                        >
                          {isSuccess && <CheckCircle2 className="mr-1 h-3 w-3" />}
                          {isFailed && <XCircle className="mr-1 h-3 w-3" />}
                          {!isSuccess && !isFailed && <AlertCircle className="mr-1 h-3 w-3" />}
                          {call.outcome}
                        </span>
                      </td>
                      <td className="text-muted-foreground max-w-xs truncate px-6 py-4">
                        {call.success_reason ? (
                          <span className="text-emerald-600 dark:text-emerald-400">
                            {call.success_reason}
                          </span>
                        ) : call.failure_reason ? (
                          <span className="text-rose-600 dark:text-rose-400">
                            {call.failure_reason}
                          </span>
                        ) : call.tool_used ? (
                          <span className="text-foreground font-mono text-xs">
                            Tool: {call.tool_used}
                          </span>
                        ) : (
                          <span className="text-muted-foreground italic">Normal conversation</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
