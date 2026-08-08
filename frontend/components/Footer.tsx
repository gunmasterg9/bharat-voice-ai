'use client';

import React from 'react';
import { Heart } from 'lucide-react';

export function Footer() {
  return (
    <footer className="border-border/40 bg-background/60 w-full border-t py-1.5 backdrop-blur-sm sm:py-2.5">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 text-center sm:flex-row sm:px-6 sm:text-left">
        {/* Language examples & Tagline */}
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
          <p className="text-foreground text-xs font-medium">
            &quot;Your voice. Your language. Your AI.&quot;
          </p>
          <span className="text-muted-foreground hidden sm:inline">•</span>
          <div className="flex items-center justify-center space-x-2 text-xs font-medium text-amber-600 dark:text-amber-400">
            <span className="rounded-md border border-amber-500/20 bg-amber-500/10 px-1.5 py-0.5">
              English
            </span>
            <span className="rounded-md border border-amber-500/20 bg-amber-500/10 px-1.5 py-0.5">
              नमस्ते
            </span>
            <span className="rounded-md border border-amber-500/20 bg-amber-500/10 px-1.5 py-0.5">
              નમસ્તે
            </span>
          </div>
        </div>

        {/* Footer Credit */}
        <p className="text-muted-foreground flex items-center text-xs">
          Built with <Heart className="mx-1 h-3 w-3 fill-amber-500 text-amber-500" /> for 10 Days of
          AI Voice Agents
        </p>
      </div>
    </footer>
  );
}
