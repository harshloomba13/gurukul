import { NextRequest, NextResponse } from 'next/server';

const VOCAL_BRIDGE_TOKEN_URL = 'https://vocalbridgeai.com/api/v1/token';

type TokenRequestBody = {
  participant_name?: string;
  session_id?: string;
};

export const runtime = 'nodejs';

async function getUpstreamError(response: Response) {
  const text = await response.text();

  try {
    const parsed = JSON.parse(text) as { detail?: string; error?: string };
    return parsed.detail || parsed.error || text;
  } catch {
    return text;
  }
}

async function proxyVoiceToken(body: TokenRequestBody = {}) {
  const apiKey = process.env.VOCAL_BRIDGE_API_KEY;

  if (!apiKey) {
    return NextResponse.json(
      { error: 'VOCAL_BRIDGE_API_KEY is not configured' },
      { status: 500 },
    );
  }

  const headers: Record<string, string> = {
    'X-API-Key': apiKey,
    'Content-Type': 'application/json',
  };

  if (process.env.VOCAL_BRIDGE_AGENT_ID) {
    headers['X-Agent-Id'] = process.env.VOCAL_BRIDGE_AGENT_ID;
  }

  const response = await fetch(VOCAL_BRIDGE_TOKEN_URL, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      participant_name: body.participant_name || 'Web User',
      ...(body.session_id ? { session_id: body.session_id } : {}),
    }),
  });

  if (!response.ok) {
    const detail = await getUpstreamError(response);
    const requiresAgentId = detail.includes('X-Agent-Id');

    return NextResponse.json(
      {
        error: requiresAgentId
          ? 'Vocal Bridge requires VOCAL_BRIDGE_AGENT_ID for this account API key'
          : 'Failed to get voice token',
        status: response.status,
        detail,
      },
      { status: response.status },
    );
  }

  const data = await response.json();
  return NextResponse.json(data);
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json().catch(() => ({}))) as TokenRequestBody;
    return await proxyVoiceToken(body);
  } catch {
    return NextResponse.json(
      { error: 'Failed to get voice token' },
      { status: 500 },
    );
  }
}

export async function GET() {
  try {
    return await proxyVoiceToken();
  } catch {
    return NextResponse.json(
      { error: 'Failed to get voice token' },
      { status: 500 },
    );
  }
}
