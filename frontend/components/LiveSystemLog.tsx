'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Activity, Cpu, Microchip, Radio, Terminal, Volume2 } from 'lucide-react';
import { useAgent, useSessionContext } from '@livekit/components-react';
import { AgentUIState } from './AgentStatus';

interface LiveSystemLogProps {
  status: AgentUIState;
}

interface LogEntry {
  id: string;
  time: string;
  category: 'SYSTEM' | 'STT' | 'LLM' | 'TTS' | 'WEBRTC';
  message: string;
  level: 'info' | 'success' | 'warning' | 'error';
}

export function LiveSystemLog({ status }: LiveSystemLogProps) {
  const session = useSessionContext();
  const agent = useAgent();
  const [isOpen, setIsOpen] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Helper to append log entries
  const addLog = (
    category: LogEntry['category'],
    message: string,
    level: LogEntry['level'] = 'info'
  ) => {
    const time = new Date().toLocaleTimeString([], {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    setLogs((prev) => [
      ...prev.slice(-49),
      { id: `${Date.now()}-${Math.random()}`, time, category, message, level },
    ]);
  };

  // Initial page load log
  useEffect(() => {
    addLog('SYSTEM', 'Bharat Voice AI pipeline initialized (Day 3 Edition)', 'info');
    addLog('STT', 'Deepgram Nova-3 STT ready', 'info');
    addLog('TTS', 'Murf Falcon TTS (Pooja Voice) ready', 'info');
    addLog('LLM', 'LLM Provider active (OpenAI / Gemini)', 'info');
  }, []);

  // Sync logs based on status changes
  useEffect(() => {
    if (status === 'CONNECTING') {
      addLog('WEBRTC', 'Establishing WebRTC session to LiveKit room...', 'warning');
    } else if (status === 'LISTENING') {
      addLog('STT', 'User speech detected — listening via Deepgram Nova-3', 'info');
    } else if (status === 'SPEAKING') {
      addLog('TTS', 'Streaming audio response via Murf Falcon TTS', 'success');
      addLog('LLM', 'LLM inference turn complete', 'success');
    } else if (status === 'CALL_ENDED') {
      addLog('WEBRTC', 'Voice call disconnected cleanly', 'info');
    } else if (status === 'PERMISSION_ERROR') {
      addLog('SYSTEM', 'Microphone access blocked by browser', 'error');
    } else if (status === 'CONNECTION_ERROR') {
      addLog('WEBRTC', 'LiveKit WebRTC connection error', 'error');
    }
  }, [status]);

  // Track session connection state
  useEffect(() => {
    if (session.isConnected) {
      addLog('WEBRTC', `Room connected: ${session.room?.name || 'Live Room'}`, 'success');
    }
  }, [session.isConnected, session.room?.name]);

  // Track agent state
  useEffect(() => {
    if (agent.state === 'thinking') {
      addLog('LLM', 'Processing user prompt via LLM...', 'info');
    }
  }, [agent.state]);

  // Auto-scroll logs
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, isOpen]);

  return (
    <div className="w-full">
      {/* Drawer Toggle Bar */}
      <div className="bg-muted/40 border-border/50 flex items-center justify-between rounded-xl border px-3 py-1.5 text-xs">
        <div className="text-muted-foreground flex items-center space-x-3 overflow-x-auto py-0.5">
          <span className="flex items-center text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
            <Radio className="mr-1 h-3 w-3 animate-pulse text-emerald-500" />
            LiveKit WebRTC
          </span>
          <span>•</span>
          <span className="flex items-center text-[11px] font-semibold text-blue-600 dark:text-blue-400">
            <Microchip className="mr-1 h-3 w-3 text-blue-500" />
            STT: Deepgram Nova-3
          </span>
          <span>•</span>
          <span className="flex items-center text-[11px] font-semibold text-amber-600 dark:text-amber-400">
            <Volume2 className="mr-1 h-3 w-3 text-amber-500" />
            TTS: Murf Falcon
          </span>
          <span>•</span>
          <span className="flex items-center text-[11px] font-semibold text-indigo-600 dark:text-indigo-400">
            <Cpu className="mr-1 h-3 w-3 text-indigo-500" />
            LLM Active
          </span>
        </div>

        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="border-border/60 bg-background/80 text-foreground hover:bg-muted ml-2 flex shrink-0 items-center space-x-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-medium transition-colors"
        >
          <Terminal className="h-3.5 w-3.5 text-amber-500" />
          <span>{isOpen ? 'Hide API Logs' : 'API Logs'}</span>
          <span className="py-0.2 ml-1 rounded-full bg-amber-500/20 px-1.5 text-[10px] font-bold text-amber-600 dark:text-amber-400">
            {logs.length}
          </span>
        </button>
      </div>

      {/* Terminal Log Console */}
      {isOpen && (
        <div className="mt-2 rounded-2xl border border-slate-800 bg-slate-950 p-3 font-mono text-[11px] text-slate-100 shadow-xl">
          <div className="mb-2 flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2">
              <Activity className="h-3.5 w-3.5 animate-pulse text-emerald-400" />
              <span className="font-bold text-slate-200">System & Pipeline Diagnostics</span>
            </div>
            <span className="text-[10px] text-slate-400">Auto-scroll Active</span>
          </div>

          <div
            ref={scrollRef}
            className="scrollbar-thin scrollbar-thumb-slate-800 h-36 space-y-1 overflow-y-auto pr-1"
          >
            {logs.map((log) => {
              const categoryColors = {
                SYSTEM: 'text-purple-400',
                STT: 'text-blue-400',
                LLM: 'text-indigo-400',
                TTS: 'text-amber-400',
                WEBRTC: 'text-emerald-400',
              };

              const levelColors = {
                info: 'text-slate-300',
                success: 'text-emerald-400 font-medium',
                warning: 'text-amber-300',
                error: 'text-red-400 font-bold',
              };

              return (
                <div key={log.id} className="flex items-start space-x-2 leading-tight">
                  <span className="shrink-0 text-slate-500">[{log.time}]</span>
                  <span className={`shrink-0 font-bold ${categoryColors[log.category]}`}>
                    [{log.category}]
                  </span>
                  <span className={levelColors[log.level]}>{log.message}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
