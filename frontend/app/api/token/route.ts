import { NextResponse } from 'next/server';
import { AccessToken, type AccessTokenOptions, type VideoGrant } from 'livekit-server-sdk';
import { RoomConfiguration } from '@livekit/protocol';

type ConnectionDetails = {
  serverUrl: string;
  roomName: string;
  participantName: string;
  participantToken: string;
  token: string;
  accessToken: string;
};

// Environment variables
export const revalidate = 0;

export async function GET(req: Request) {
  return POST(req);
}

export async function POST(req: Request) {
  try {
    const apiKey = process.env.LIVEKIT_API_KEY || 'APIxkgoTqTQrjHf';
    const apiSecret =
      process.env.LIVEKIT_API_SECRET || '3euNjMdJ1XsMt5QCUCuvCOVUq8eeYJGL0teAWIdnGv0B';
    const livekitUrl =
      process.env.LIVEKIT_URL || 'wss://murf-ai-voice-agent-challenge-8swhjxgh.livekit.cloud';
    const agentName = process.env.AGENT_NAME || 'bharat-voice-ai';

    if (!livekitUrl) {
      throw new Error('LIVEKIT_URL is not defined in environment variables');
    }
    if (!apiKey) {
      throw new Error('LIVEKIT_API_KEY is not defined in environment variables');
    }
    if (!apiSecret) {
      throw new Error('LIVEKIT_API_SECRET is not defined in environment variables');
    }

    // Support both query string params and request body safely
    const { searchParams } = new URL(req.url);
    const queryUserId = searchParams.get('userId') || searchParams.get('user_id');

    let body: Record<string, unknown> = {};
    if (req.method === 'POST') {
      try {
        body = (await req.json()) as Record<string, unknown>;
      } catch {
        body = {};
      }
    }

    let roomConfig: RoomConfiguration | undefined;
    if (body?.room_config) {
      roomConfig = RoomConfiguration.fromJson(JSON.parse(JSON.stringify(body.room_config)), {
        ignoreUnknownFields: true,
      });
    } else if (agentName) {
      roomConfig = RoomConfiguration.fromJson(
        { agents: [{ agentName }] },
        { ignoreUnknownFields: true }
      );
    }

    // Accept persistent caller ID from query param, body, or generate fallback
    const requestedUserId = queryUserId || body?.userId || body?.user_id;
    const participantIdentity = requestedUserId
      ? String(requestedUserId)
      : 'default_user';

    const participantName = 'user';
    const roomName =
      (body?.roomName as string) || `voice_assistant_room_${Math.floor(Math.random() * 10_000)}`;

    const participantToken = await createParticipantToken(
      { identity: participantIdentity, name: participantName },
      roomName,
      apiKey,
      apiSecret,
      roomConfig
    );

    const data: ConnectionDetails = {
      serverUrl: livekitUrl,
      roomName,
      participantName,
      participantToken,
      token: participantToken,
      accessToken: participantToken,
    };
    const headers = new Headers({
      'Cache-Control': 'no-store',
      'Access-Control-Allow-Origin': '*',
    });
    return NextResponse.json(data, { headers });
  } catch (error) {
    console.error('[TOKEN API ERROR]', error);
    const msg = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

function createParticipantToken(
  userInfo: AccessTokenOptions,
  roomName: string,
  apiKey: string,
  apiSecret: string,
  roomConfig?: RoomConfiguration
): Promise<string> {
  const at = new AccessToken(apiKey, apiSecret, {
    ...userInfo,
    ttl: '15m',
  });
  const grant: VideoGrant = {
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canPublishData: true,
    canSubscribe: true,
  };
  at.addGrant(grant);

  if (roomConfig) {
    at.roomConfig = roomConfig;
  }

  return at.toJwt();
}
