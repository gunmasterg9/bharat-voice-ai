'use client';

import React from 'react';
import { useLocalParticipant, useVoiceAssistant } from '@livekit/components-react';
import { AgentAudioVisualizerBar } from '@/components/agents-ui/agent-audio-visualizer-bar';
import { AgentUIState } from './AgentStatus';

interface AudioVisualizerProps {
  status: AgentUIState;
}

export function AudioVisualizer({ status }: AudioVisualizerProps) {
  const { audioTrack: agentAudioTrack } = useVoiceAssistant();
  const { microphoneTrack } = useLocalParticipant();

  // Active track based on who is speaking
  const isAgentSpeaking = status === 'SPEAKING';
  const isUserSpeaking = status === 'LISTENING';
  const activeTrack = (isAgentSpeaking ? agentAudioTrack : microphoneTrack?.track) as any;

  return (
    <div className="relative flex items-center justify-center py-1 sm:py-2">
      {/* Outer Glow Ring */}
      <div
        className={`absolute rounded-full blur-2xl transition-all duration-500 ${
          isAgentSpeaking
            ? 'h-36 w-36 animate-pulse bg-amber-500/30 sm:h-52 sm:w-52'
            : isUserSpeaking
              ? 'h-36 w-36 animate-pulse bg-blue-500/30 sm:h-52 sm:w-52'
              : status === 'CONNECTING'
                ? 'h-32 w-32 animate-ping bg-amber-500/20 sm:h-44 sm:w-44'
                : 'bg-muted/20 h-28 w-28'
        }`}
      />

      {/* Dynamic Animated Visualizer Container */}
      <div className="border-border/50 bg-card/60 relative z-10 flex h-32 w-full max-w-md items-center justify-center rounded-3xl border p-3 shadow-inner backdrop-blur-md sm:h-40 sm:p-4 md:h-44">
        {status === 'READY' || status === 'CALL_ENDED' ? (
          <div className="text-muted-foreground flex flex-col items-center justify-center space-y-1 sm:space-y-2">
            <div className="flex items-center space-x-1.5">
              {[0.4, 0.7, 1.0, 0.7, 0.4].map((scale, i) => (
                <span
                  key={i}
                  style={{ height: `${scale * 24}px` }}
                  className="bg-muted-foreground/30 w-1.5 rounded-full transition-all"
                />
              ))}
            </div>
            <span className="text-xs font-medium">
              {status === 'READY' ? 'Microphone Ready' : 'Call Completed'}
            </span>
          </div>
        ) : status === 'CONNECTING' ? (
          <div className="flex flex-col items-center justify-center space-y-2 text-amber-600 dark:text-amber-400">
            <div className="flex items-center space-x-2">
              {[0.2, 0.6, 0.9, 0.6, 0.2].map((scale, i) => (
                <span
                  key={i}
                  style={{ height: `${scale * 30}px` }}
                  className="w-2 animate-pulse rounded-full bg-amber-500"
                />
              ))}
            </div>
            <span className="text-xs font-medium tracking-wide">Connecting to Agent...</span>
          </div>
        ) : (
          <div className="flex w-full flex-col items-center justify-center">
            {/* LiveKit Track Audio Visualizer */}
            <AgentAudioVisualizerBar
              size="md"
              state={isAgentSpeaking ? 'speaking' : isUserSpeaking ? 'listening' : 'connecting'}
              audioTrack={activeTrack}
              barCount={7}
              color={isAgentSpeaking ? '#F59E0B' : '#3B82F6'}
              className="h-20 w-full max-w-xs sm:h-24"
            />
            <div className="mt-2 flex items-center space-x-2 text-xs font-semibold">
              <span
                className={`h-2 w-2 rounded-full ${
                  isAgentSpeaking
                    ? 'animate-ping bg-amber-500'
                    : isUserSpeaking
                      ? 'animate-ping bg-blue-500'
                      : 'bg-muted'
                }`}
              />
              <span className={isAgentSpeaking ? 'text-amber-500' : 'text-blue-500'}>
                {isAgentSpeaking ? 'Bharat Voice AI Output' : 'User Input Signal'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
