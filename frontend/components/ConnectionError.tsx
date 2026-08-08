'use client';

import React from 'react';
import { AlertCircle, RefreshCw, WifiOff } from 'lucide-react';

interface ConnectionErrorProps {
  onRetry: () => void;
  message?: string;
}

export function ConnectionError({ onRetry, message }: ConnectionErrorProps) {
  return (
    <div className="bg-card mx-auto my-6 max-w-md space-y-4 rounded-3xl border border-amber-500/30 p-6 text-center shadow-xl">
      {/* Network Warning Icon */}
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-amber-500/20 bg-amber-500/10 text-amber-500">
        <WifiOff className="h-7 w-7" />
      </div>

      {/* Main Error Heading */}
      <h3 className="text-foreground text-xl font-bold">Unable to connect</h3>

      {/* Supporting Guidance */}
      <p className="text-muted-foreground text-xs leading-relaxed sm:text-sm">
        {message || 'Please check your internet connection and try again.'}
      </p>

      {/* Quick check box */}
      <div className="bg-muted/60 text-muted-foreground border-border/40 space-y-1 rounded-xl border p-3 text-left text-xs">
        <div className="text-foreground flex items-center space-x-1.5 font-semibold">
          <AlertCircle className="h-3.5 w-3.5 text-amber-500" />
          <span>Troubleshooting Tips:</span>
        </div>
        <ul className="list-inside list-disc space-y-0.5 pl-1">
          <li>Check Wi-Fi or cellular data connection</li>
          <li>Ensure backend voice agent server is active</li>
          <li>Verify LiveKit connection details in .env.local</li>
        </ul>
      </div>

      {/* Action Button */}
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center justify-center space-x-2 rounded-full bg-gradient-to-r from-amber-500 to-orange-600 px-6 py-3 text-xs font-bold text-white shadow-md transition-all hover:scale-105 focus:ring-2 focus:ring-amber-500/50 focus:outline-none active:scale-95"
      >
        <RefreshCw className="h-4 w-4" />
        <span>Try Again</span>
      </button>
    </div>
  );
}
