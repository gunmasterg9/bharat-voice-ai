'use client';

import { useEffect, useMemo, useState } from 'react';
import { TokenSource } from 'livekit-client';
import { useSession } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react/dist/ssr';
import type { AppConfig } from '@/app-config';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { StartAudioButton } from '@/components/agents-ui/start-audio-button';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/ui/sonner';
import { useAgentErrors } from '@/hooks/useAgentErrors';
import { useDebugMode } from '@/hooks/useDebug';
import { getSandboxTokenSource } from '@/lib/utils';

const IN_DEVELOPMENT = process.env.NODE_ENV !== 'production';

function getPersistentUserId(): string {
  if (typeof window === 'undefined') return 'caller_default_user';
  let userId = localStorage.getItem('bharat_voice_user_id');
  if (!userId) {
    userId = `caller_${Math.random().toString(36).substring(2, 10)}`;
    localStorage.setItem('bharat_voice_user_id', userId);
  }
  return userId;
}

function AppSetup() {
  useDebugMode({ enabled: IN_DEVELOPMENT });
  useAgentErrors();

  return null;
}

interface AppProps {
  appConfig: AppConfig;
}

export function App({ appConfig }: AppProps) {
  const [userId, setUserId] = useState<string>('');

  useEffect(() => {
    setUserId(getPersistentUserId());
  }, []);

  const tokenSource = useMemo(() => {
    if (typeof process.env.NEXT_PUBLIC_CONN_DETAILS_ENDPOINT === 'string') {
      return getSandboxTokenSource(appConfig);
    }
    const activeUserId =
      userId || (typeof window !== 'undefined' ? getPersistentUserId() : 'caller_default_user');
    if (typeof window !== 'undefined') {
      console.log('[MEMORY DEBUG] FRONTEND USER ID =', activeUserId);
    }
    return TokenSource.endpoint(`/api/token?userId=${encodeURIComponent(activeUserId)}`);
  }, [appConfig, userId]);

  const session = useSession(
    tokenSource,
    appConfig.agentName ? { agentName: appConfig.agentName } : undefined
  );

  return (
    <AgentSessionProvider session={session}>
      <AppSetup />
      <main className="min-h-screen w-full">
        <ViewController />
      </main>
      <StartAudioButton label="Start Audio" />
      <Toaster
        icons={{
          warning: <WarningIcon weight="bold" />,
        }}
        position="top-center"
        className="toaster group"
        style={
          {
            '--normal-bg': 'var(--popover)',
            '--normal-text': 'var(--popover-foreground)',
            '--normal-border': 'var(--border)',
          } as React.CSSProperties
        }
      />
    </AgentSessionProvider>
  );
}
