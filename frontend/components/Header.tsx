'use client';

import React from 'react';
import { Headphones, Mic, Radio, ShieldCheck, Sparkles } from 'lucide-react';
import { ThemeToggle } from '@/components/app/theme-toggle';

interface HeaderProps {
  status:
    | 'READY'
    | 'CONNECTING'
    | 'LISTENING'
    | 'SPEAKING'
    | 'CALL_ENDED'
    | 'PERMISSION_ERROR'
    | 'CONNECTION_ERROR';
  activeView?: 'agent' | 'human-help';
  onViewChange?: (view: 'agent' | 'human-help') => void;
}

export function Header({ status, activeView = 'agent', onViewChange }: HeaderProps) {
  const isConnected = status === 'LISTENING' || status === 'SPEAKING';
  const isConnecting = status === 'CONNECTING';

  return (
    <header className="border-border/40 bg-background/80 sticky top-0 z-40 w-full border-b backdrop-blur-md transition-colors">
      <div className="mx-auto flex h-12 max-w-7xl items-center justify-between px-3 sm:h-14 sm:px-6 md:h-16 lg:px-8">
        {/* Brand Logo & Name */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          <div className="relative flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-amber-500 via-orange-500 to-indigo-600 shadow-md shadow-amber-500/20 sm:h-9 sm:w-9 md:h-10 md:w-10">
            <Mic className="h-4 w-4 text-white sm:h-5 sm:w-5" />
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex h-3 w-3 rounded-full bg-amber-500"></span>
            </span>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-foreground font-sans text-lg font-bold tracking-tight sm:text-xl">
                Bharat Voice AI
              </h1>
              <span className="inline-flex items-center rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-600 dark:text-amber-400">
                <Sparkles className="mr-1 h-3 w-3" />
                Day 7
              </span>
            </div>
            <p className="text-muted-foreground hidden text-xs sm:block">
              Voice for Bharat Edition
            </p>
          </div>
        </div>

        {/* View Switcher Tabs & Controls */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {onViewChange && (
            <div className="border-border bg-muted/40 flex items-center rounded-xl border p-1">
              <button
                onClick={() => onViewChange('agent')}
                className={`flex items-center space-x-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all ${
                  activeView === 'agent'
                    ? 'bg-background text-foreground border-border border shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Mic className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Voice Agent</span>
              </button>

              <button
                onClick={() => onViewChange('human-help')}
                className={`flex items-center space-x-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all ${
                  activeView === 'human-help'
                    ? 'border border-amber-500/30 bg-amber-500/20 text-amber-600 dark:text-amber-300'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Headphones className="h-3.5 w-3.5 text-amber-500" />
                <span>Human Help</span>
              </button>
            </div>
          )}

          {/* Memory Status Badge */}
          <div className="hidden items-center space-x-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-700 sm:flex dark:text-amber-300">
            <ShieldCheck className="h-3.5 w-3.5 text-amber-500" />
            <span>Escalation: Ready</span>
          </div>

          {/* Connection Status Pill */}
          <div className="border-border/60 bg-muted/50 text-foreground flex items-center space-x-2 rounded-full border px-3 py-1 text-xs font-medium">
            <Radio
              className={`h-3.5 w-3.5 ${
                isConnected
                  ? 'animate-pulse text-emerald-500'
                  : isConnecting
                    ? 'animate-spin text-amber-500'
                    : 'text-muted-foreground'
              }`}
            />
            <span className="capitalize">
              {isConnected ? 'Live Agent' : isConnecting ? 'Connecting...' : 'Offline'}
            </span>
          </div>

          {/* Color Scheme Switcher */}
          <div className="w-auto">
            <ThemeToggle className="border-border/60 bg-muted/40 w-auto" />
          </div>
        </div>
      </div>
    </header>
  );
}
