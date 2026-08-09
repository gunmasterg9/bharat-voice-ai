'use client';

import React from 'react';
import { AlertTriangle, Loader2, Mic, PhoneOff, User, Volume2 } from 'lucide-react';

export type AgentUIState =
  | 'READY'
  | 'CONNECTING'
  | 'LISTENING'
  | 'SPEAKING'
  | 'CALL_ENDED'
  | 'PERMISSION_ERROR'
  | 'CONNECTION_ERROR';

interface AgentStatusProps {
  status: AgentUIState;
  detectedLanguage?: string;
  micLabel?: string;
}

export function AgentStatus({ status, detectedLanguage, micLabel }: AgentStatusProps) {
  const renderStateDetails = () => {
    switch (status) {
      case 'READY':
        return {
          title: 'Bharat Voice AI',
          tagline: 'Your voice. Your language. Your AI.',
          subtitle: 'Talk naturally with an AI assistant built for India.',
          badge: 'Ready to talk',
          badgeColor:
            'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
          icon: <Mic className="h-6 w-6 text-amber-500" />,
        };
      case 'CONNECTING':
        return {
          title: 'Connecting...',
          tagline: 'Establishing secure LiveKit audio channel',
          subtitle: 'Please wait while we connect you to Bharat Voice AI.',
          badge: 'Connecting',
          badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
          icon: <Loader2 className="h-6 w-6 animate-spin text-amber-500" />,
        };
      case 'LISTENING':
        return {
          title: 'Listening to you',
          tagline: 'Speaker: You',
          subtitle: 'Speak freely in English, Hindi, Gujarati, or Hinglish.',
          badge: 'User Speaking',
          badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
          icon: <User className="h-6 w-6 animate-pulse text-blue-500" />,
        };
      case 'SPEAKING':
        return {
          title: 'Bharat Voice AI is speaking',
          tagline: 'Speaker: Bharat Voice AI',
          subtitle: 'Streaming response via Murf Falcon TTS...',
          badge: 'Agent Speaking',
          badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
          icon: <Volume2 className="h-6 w-6 animate-bounce text-amber-500" />,
        };
      case 'CALL_ENDED':
        return {
          title: 'Conversation ended',
          tagline: 'Call finished cleanly',
          subtitle: 'Thanks for talking with Bharat Voice AI.',
          badge: 'Call Ended',
          badgeColor: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20',
          icon: <PhoneOff className="h-6 w-6 text-slate-400" />,
        };
      case 'PERMISSION_ERROR':
        return {
          title: 'Microphone access is blocked',
          tagline: 'Permissions required',
          subtitle: 'Please allow microphone access in your browser settings and try again.',
          badge: 'Permission Blocked',
          badgeColor: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
          icon: <AlertTriangle className="h-6 w-6 text-red-500" />,
        };
      case 'CONNECTION_ERROR':
        return {
          title: 'Unable to connect',
          tagline: 'Network or server issue',
          subtitle: 'Please check your internet connection and try again.',
          badge: 'Connection Error',
          badgeColor: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
          icon: <AlertTriangle className="h-6 w-6 text-red-500" />,
        };
      default:
        return {
          title: 'Bharat Voice AI',
          tagline: 'Your voice. Your language. Your AI.',
          subtitle: 'Talk naturally with an AI assistant built for India.',
          badge: 'Ready',
          badgeColor: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20',
          icon: <Mic className="h-6 w-6 text-amber-500" />,
        };
    }
  };

  const details = renderStateDetails();

  return (
    <div className="mx-auto flex max-w-xl flex-col items-center space-y-1.5 px-4 text-center sm:space-y-2">
      {/* State Badge & Icon */}
      <div className="flex items-center space-x-2">
        <div className="bg-card border-border rounded-2xl border p-2 shadow-sm sm:p-2.5">
          {details.icon}
        </div>
        <span
          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold sm:px-3 sm:py-1 ${details.badgeColor}`}
        >
          {details.badge}
        </span>
        {micLabel && (
          <span className="inline-flex items-center rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-600 sm:px-3 sm:py-1 dark:text-amber-400">
            Mic: {micLabel}
          </span>
        )}
        {detectedLanguage && (
          <span className="inline-flex items-center rounded-full border border-indigo-500/20 bg-indigo-500/10 px-2.5 py-0.5 text-xs font-semibold text-indigo-600 sm:px-3 sm:py-1 dark:text-indigo-400">
            Language: {detectedLanguage}
          </span>
        )}
      </div>

      {/* Main Title */}
      <h2 className="text-foreground text-lg font-extrabold tracking-tight sm:text-2xl md:text-3xl">
        {details.title}
      </h2>

      {/* Tagline or Subtitle */}
      {status === 'READY' && (
        <p className="text-xs font-semibold text-amber-600 sm:text-sm dark:text-amber-400">
          &quot;{details.tagline}&quot;
        </p>
      )}

      {/* Supporting text */}
      <p className="text-muted-foreground text-[11px] leading-snug sm:text-xs md:text-sm">
        {details.subtitle}
      </p>

      {/* Multilingual visual preview on READY state */}
      {status === 'READY' && (
        <div className="text-foreground/80 flex items-center justify-center space-x-3 pt-0.5 text-xs font-medium sm:text-sm">
          <span>નમસ્તે</span>
          <span className="text-amber-500">•</span>
          <span>नमस्ते</span>
          <span className="text-amber-500">•</span>
          <span>Hello</span>
        </div>
      )}
    </div>
  );
}
