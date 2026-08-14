'use client';

import { type ComponentProps } from 'react';
import { AnimatePresence } from 'motion/react';
import { type AgentState, type ReceivedMessage } from '@livekit/components-react';
import { AgentChatIndicator } from '@/components/agents-ui/agent-chat-indicator';
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from '@/components/ai-elements/conversation';
import { Message, MessageContent, MessageResponse } from '@/components/ai-elements/message';

/**
 * Props for the AgentChatTranscript component.
 */
export interface AgentChatTranscriptProps extends ComponentProps<'div'> {
  /**
   * The current state of the agent. When 'thinking', displays a loading indicator.
   */
  agentState?: AgentState;
  /**
   * Array of messages to display in the transcript.
   * @defaultValue []
   */
  messages?: ReceivedMessage[];
  /**
   * Additional CSS class names to apply to the conversation container.
   */
  className?: string;
}

/**
 * A chat transcript component that displays a conversation between the user and agent.
 * Shows messages with timestamps and origin indicators, plus a thinking indicator
 * when the agent is processing.
 *
 * @extends ComponentProps<'div'>
 *
 * @example
 * ```tsx
 * <AgentChatTranscript
 *   agentState={agentState}
 *   messages={chatMessages}
 * />
 * ```
 */
const isJsonOrFunctionCall = (msg: string) => {
  if (!msg) return false;
  const trimmed = msg.trim();
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) return true;
  if (
    trimmed.includes('This JSON response is for a function call') ||
    trimmed.includes('function_call') ||
    trimmed.includes('The function called is')
  ) {
    return true;
  }
  return false;
};

export function AgentChatTranscript({
  agentState,
  messages = [],
  className,
  ...props
}: AgentChatTranscriptProps) {
  return (
    <Conversation className={className} {...props}>
      <ConversationContent>
        {messages
          .filter((m) => !isJsonOrFunctionCall(m.message))
          .map((receivedMessage) => {
            const { id, timestamp, from, message } = receivedMessage;
            const locale = navigator?.language ?? 'en-US';
            const messageOrigin = from?.isLocal ? 'user' : 'assistant';
            const time = new Date(timestamp);
            const title = time.toLocaleTimeString(locale, { timeStyle: 'full' });

            return (
              <Message key={id} title={title} from={messageOrigin}>
                <MessageContent>
                  <MessageResponse>{message}</MessageResponse>
                </MessageContent>
              </Message>
            );
          })}
        <AnimatePresence>
          {agentState === 'thinking' && <AgentChatIndicator size="sm" />}
        </AnimatePresence>
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>
  );
}
