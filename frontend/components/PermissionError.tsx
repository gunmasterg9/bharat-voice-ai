'use client';

import React from 'react';
import { MicOff, RefreshCw, ShieldAlert } from 'lucide-react';

interface PermissionErrorProps {
  onRetry: () => void;
}

export function PermissionError({ onRetry }: PermissionErrorProps) {
  return (
    <div className="bg-card mx-auto my-6 max-w-md space-y-4 rounded-3xl border border-red-500/30 p-6 text-center shadow-xl">
      {/* Warning Icon */}
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-red-500/20 bg-red-500/10 text-red-500">
        <MicOff className="h-7 w-7" />
      </div>

      {/* Main Error Heading */}
      <h3 className="text-foreground text-xl font-bold">Microphone access is blocked.</h3>

      {/* Clear Guidance */}
      <p className="text-muted-foreground text-xs leading-relaxed sm:text-sm">
        Please allow microphone access in your browser settings and try again.
      </p>

      {/* Step-by-step helper */}
      <div className="bg-muted/60 text-muted-foreground border-border/40 space-y-1.5 rounded-xl border p-3 text-left text-xs">
        <div className="text-foreground flex items-center space-x-1.5 font-semibold">
          <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
          <span>How to enable microphone:</span>
        </div>
        <ol className="list-inside list-decimal space-y-1 pl-1">
          <li>Click the lock icon next to the address bar.</li>
          <li>
            Toggle <strong>Microphone</strong> to <strong>Allow</strong>.
          </li>
          <li>
            Click <strong>Try Again</strong> below.
          </li>
        </ol>
      </div>

      {/* Action Button */}
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center justify-center space-x-2 rounded-full bg-gradient-to-r from-red-600 to-rose-600 px-6 py-3 text-xs font-bold text-white shadow-md transition-all hover:scale-105 focus:ring-2 focus:ring-red-500/50 focus:outline-none active:scale-95"
      >
        <RefreshCw className="h-4 w-4" />
        <span>Try Again</span>
      </button>
    </div>
  );
}
