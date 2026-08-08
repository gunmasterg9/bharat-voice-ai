'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Bot, ChevronDown, ChevronUp, MessageSquare, User } from 'lucide-react';
import { useSessionContext, useSessionMessages } from '@livekit/components-react';

export function ConversationTranscript() {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const [isOpen, setIsOpen] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const messageCount = messages?.length || 0;

  return (
    <div className="h-full w-full p-1">
      <div className="border-border/60 bg-card/80 flex h-full flex-col overflow-hidden rounded-2xl border shadow-lg backdrop-blur-md transition-all">
        {/* Card Header & Toggle */}
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="border-border/40 text-foreground hover:bg-muted/40 flex w-full items-center justify-between border-b px-4 py-2.5 text-left text-xs font-semibold transition-colors"
        >
          <div className="flex items-center space-x-2">
            <MessageSquare className="h-4 w-4 text-amber-500" />
            <span>Live Conversation Transcript ({messageCount})</span>
          </div>
          {isOpen ? (
            <ChevronUp className="text-muted-foreground h-4 w-4" />
          ) : (
            <ChevronDown className="text-muted-foreground h-4 w-4" />
          )}
        </button>

        {/* Collapsible Transcript Body */}
        {isOpen && (
          <div
            ref={scrollRef}
            className="scrollbar-thin scrollbar-thumb-muted max-h-[320px] min-h-[220px] flex-1 space-y-3 overflow-y-auto p-3 sm:max-h-[380px] sm:p-4 md:max-h-[420px]"
          >
            {messageCount === 0 ? (
              <div className="flex h-full min-h-[180px] flex-col items-center justify-center space-y-2 p-6 text-center">
                <MessageSquare className="h-8 w-8 animate-pulse text-amber-500/40" />
                <p className="text-foreground text-xs font-semibold sm:text-sm">
                  Live Transcript Ready
                </p>
                <p className="text-muted-foreground max-w-xs text-[11px] leading-relaxed sm:text-xs">
                  Speak into your microphone or ask a question. Real-time text output from Bharat
                  Voice AI will stream here.
                </p>
              </div>
            ) : (
              messages.map((msg, index) => {
                const isUser = Boolean(
                  msg.from?.isLocal ||
                    (msg.from?.identity && !msg.from.identity.toLowerCase().includes('agent'))
                );

                return (
                  <div
                    key={msg.id || index}
                    className={`flex space-x-2.5 text-xs sm:text-sm ${
                      isUser ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    {!isUser && (
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-amber-500/20 bg-amber-500/10 text-amber-600 dark:text-amber-400">
                        <Bot className="h-4 w-4" />
                      </div>
                    )}

                    <div
                      className={`max-w-[82%] rounded-2xl px-3.5 py-2.5 leading-relaxed shadow-xs ${
                        isUser
                          ? 'rounded-br-none bg-blue-600 font-medium text-white'
                          : 'bg-muted/80 text-foreground border-border/50 rounded-bl-none border'
                      }`}
                    >
                      <div className="mb-1 flex items-center justify-between space-x-2 text-[10px] font-semibold opacity-80">
                        <span>{isUser ? 'You' : 'Bharat Voice AI'}</span>
                      </div>
                      <p>{msg.message}</p>
                    </div>

                    {isUser && (
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-blue-500/20 bg-blue-500/10 text-blue-600 dark:text-blue-400">
                        <User className="h-4 w-4" />
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}
