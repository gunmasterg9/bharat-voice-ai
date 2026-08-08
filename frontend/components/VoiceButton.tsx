'use client';

import React from 'react';
import { Loader2, Mic, PhoneOff, RotateCcw } from 'lucide-react';
import { AgentUIState } from './AgentStatus';

interface VoiceButtonProps {
  status: AgentUIState;
  onStart: () => void;
  onEnd: () => void;
  onRestart: () => void;
  disabled?: boolean;
}

export function VoiceButton({
  status,
  onStart,
  onEnd,
  onRestart,
  disabled = false,
}: VoiceButtonProps) {
  const isConnected = status === 'LISTENING' || status === 'SPEAKING';
  const isConnecting = status === 'CONNECTING';

  if (isConnected) {
    return (
      <div className="group relative">
        <div className="absolute -inset-1 animate-pulse rounded-full bg-gradient-to-r from-red-500 to-rose-600 opacity-75 blur transition duration-300 group-hover:opacity-100"></div>
        <button
          type="button"
          onClick={onEnd}
          aria-label="End voice conversation"
          className="relative flex items-center justify-center space-x-3 rounded-full bg-gradient-to-r from-red-600 to-rose-700 px-8 py-4 text-base font-bold text-white shadow-xl transition-all duration-200 hover:scale-105 focus:ring-4 focus:ring-red-500/50 focus:outline-none active:scale-95"
        >
          <PhoneOff className="h-6 w-6" />
          <span>End Conversation</span>
        </button>
      </div>
    );
  }

  if (isConnecting) {
    return (
      <button
        type="button"
        disabled
        aria-label="Connecting to Bharat Voice AI"
        className="flex cursor-not-allowed items-center justify-center space-x-3 rounded-full bg-amber-500/50 px-8 py-4 text-base font-bold text-white opacity-80 shadow-md"
      >
        <Loader2 className="h-6 w-6 animate-spin" />
        <span>Connecting...</span>
      </button>
    );
  }

  if (status === 'CALL_ENDED') {
    return (
      <div className="group relative">
        <div className="absolute -inset-1 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 opacity-70 blur transition duration-300 group-hover:opacity-100"></div>
        <button
          type="button"
          onClick={onRestart}
          disabled={disabled}
          aria-label="Start conversation again"
          className="relative flex items-center justify-center space-x-3 rounded-full bg-gradient-to-r from-amber-500 to-orange-600 px-8 py-4 text-base font-bold text-white shadow-xl transition-all duration-200 hover:scale-105 focus:ring-4 focus:ring-amber-500/50 focus:outline-none active:scale-95 disabled:opacity-50"
        >
          <RotateCcw className="h-6 w-6" />
          <span>Start Again</span>
        </button>
      </div>
    );
  }

  // READY / Default state
  return (
    <div className="group relative">
      <div className="absolute -inset-1 animate-pulse rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-indigo-600 opacity-70 blur-md transition duration-300 group-hover:opacity-100 group-hover:blur-lg"></div>
      <button
        type="button"
        onClick={onStart}
        disabled={disabled}
        aria-label="Start voice conversation"
        className="relative flex items-center justify-center space-x-2.5 rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-indigo-600 px-6 py-3 text-sm font-extrabold text-white shadow-xl transition-all duration-200 hover:scale-105 focus:ring-4 focus:ring-amber-500/50 focus:outline-none active:scale-95 disabled:opacity-50 sm:px-8 sm:py-3.5 sm:text-base md:text-lg"
      >
        <Mic className="h-5 w-5 text-white sm:h-6 sm:w-6" />
        <span>Start Conversation</span>
      </button>
    </div>
  );
}
