'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useAgent, useSessionContext } from '@livekit/components-react';
import { AgentStatus, AgentUIState } from '@/components/AgentStatus';
import { AudioVisualizer } from '@/components/AudioVisualizer';
import { ConnectionError } from '@/components/ConnectionError';
import { ConversationTranscript } from '@/components/ConversationTranscript';
import { Footer } from '@/components/Footer';
import { Header } from '@/components/Header';
import { LiveSystemLog } from '@/components/LiveSystemLog';
import { PermissionError } from '@/components/PermissionError';
import { VoiceButton } from '@/components/VoiceButton';
import { AgentControlBar } from '@/components/agents-ui/agent-control-bar';

export function VoiceAgent() {
  const session = useSessionContext();
  const agent = useAgent();

  const [uiState, setUiState] = useState<AgentUIState>('READY');
  const [errorMessage, setErrorMessage] = useState<string | undefined>(undefined);
  const [chatOpen, setChatOpen] = useState(false);

  // Sync LiveKit connection & agent state to UI state
  useEffect(() => {
    if (uiState === 'PERMISSION_ERROR') {
      return;
    }

    if (session.error) {
      setUiState('CONNECTION_ERROR');
      setErrorMessage(session.error.message || 'Connection to LiveKit server failed.');
      return;
    }

    if (agent.state === 'failed') {
      setUiState('CONNECTION_ERROR');
      setErrorMessage('Agent pipeline failure. Please verify backend agent status.');
      return;
    }

    if (session.isConnecting) {
      setUiState('CONNECTING');
      return;
    }

    if (session.isConnected) {
      if (agent.state === 'speaking') {
        setUiState('SPEAKING');
      } else {
        setUiState('LISTENING');
      }
      return;
    }
  }, [session.isConnected, session.isConnecting, session.error, agent.state, uiState]);

  // Request & verify microphone permissions before connecting
  const checkMicrophonePermission = async (): Promise<boolean> => {
    if (typeof window === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setUiState('PERMISSION_ERROR');
      return false;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Stop temporary track immediately after verification
      stream.getTracks().forEach((track) => track.stop());
      return true;
    } catch (err: unknown) {
      console.error('Microphone permission check failed:', err);
      setUiState('PERMISSION_ERROR');
      return false;
    }
  };

  // Start Call Handler
  const handleStartCall = useCallback(async () => {
    setErrorMessage(undefined);
    setUiState('CONNECTING');

    const hasMicPermission = await checkMicrophonePermission();
    if (!hasMicPermission) {
      return;
    }

    try {
      await session.start();
    } catch (err: unknown) {
      console.error('Failed to start session:', err);
      setUiState('CONNECTION_ERROR');
      const msg = err instanceof Error ? err.message : 'Failed to start LiveKit voice session.';
      setErrorMessage(msg);
    }
  }, [session]);

  // End Call Handler
  const handleEndCall = useCallback(() => {
    try {
      session.end();
    } catch (err) {
      console.error('Error disconnecting session:', err);
    } finally {
      setUiState('CALL_ENDED');
    }
  }, [session]);

  // Restart Handler (Start Again)
  const handleRestartCall = useCallback(() => {
    handleStartCall();
  }, [handleStartCall]);

  return (
    <div className="from-background via-background/95 to-muted/30 text-foreground flex h-dvh max-h-dvh flex-col overflow-hidden bg-gradient-to-b selection:bg-amber-500 selection:text-white">
      {/* Header Bar */}
      <Header status={uiState} />

      {/* Main Voice Workspace */}
      <main className="flex flex-1 flex-col items-center justify-center overflow-y-auto px-4 py-2 sm:px-6">
        {session.isConnected ? (
          /* Side-by-side 2-column layout when connected */
          <div className="grid w-full max-w-5xl grid-cols-1 items-start gap-4 md:grid-cols-12 md:gap-6">
            {/* Left Column: Status, Visualizer, Control Bar */}
            <div className="flex flex-col items-center justify-center space-y-2 sm:space-y-3 md:col-span-6">
              <AgentStatus status={uiState} />
              <AudioVisualizer status={uiState} />
              <div className="w-full max-w-md pt-1">
                <AgentControlBar
                  variant="livekit"
                  isConnected={session.isConnected}
                  isChatOpen={chatOpen}
                  onIsChatOpenChange={setChatOpen}
                  onDisconnect={handleEndCall}
                  controls={{
                    leave: true,
                    microphone: true,
                    camera: false,
                    screenShare: false,
                    chat: true,
                  }}
                />
              </div>
            </div>

            {/* Right Column: Live Conversation Transcript & System API Logs */}
            <div className="flex h-full w-full flex-col justify-center space-y-3 md:col-span-6">
              <ConversationTranscript />
              <LiveSystemLog status={uiState} />
            </div>
          </div>
        ) : (
          /* Centered single-column layout before call / on error / after call */
          <div className="w-full max-w-3xl space-y-2 text-center sm:space-y-4">
            {/* Active Agent Status Header */}
            <AgentStatus status={uiState} />

            {/* Central Visualizer Area */}
            {uiState !== 'PERMISSION_ERROR' && uiState !== 'CONNECTION_ERROR' && (
              <AudioVisualizer status={uiState} />
            )}

            {/* Error Views */}
            {uiState === 'PERMISSION_ERROR' && <PermissionError onRetry={handleStartCall} />}

            {uiState === 'CONNECTION_ERROR' && (
              <ConnectionError onRetry={handleStartCall} message={errorMessage} />
            )}

            {/* Voice Button when pre/post call */}
            {uiState !== 'PERMISSION_ERROR' && uiState !== 'CONNECTION_ERROR' && (
              <div className="flex items-center justify-center pt-1 pb-2">
                <VoiceButton
                  status={uiState}
                  onStart={handleStartCall}
                  onEnd={handleEndCall}
                  onRestart={handleRestartCall}
                />
              </div>
            )}

            {/* Live System & API Diagnostics Bar */}
            <div className="w-full pt-1">
              <LiveSystemLog status={uiState} />
            </div>
          </div>
        )}
      </main>

      {/* Footer Bar */}
      <Footer />
    </div>
  );
}
