## Minions Runbook

Use these commands for the ticket runner workflow:

```bash
# Reset state for every ticket file under tickets/
python3 quarter.py reset

# Reset one ticket
python3 quarter.py reset --ticket GURU-106

# Run selected tickets in parallel
python3 quarter.py run --runner codex-ollama --draft-pr

# Force sequential runs
python3 quarter.py run --runner codex-ollama --draft-pr --sequential

# Run only tickets assigned to minion
python3 quarter.py watch --assigned-to minion --once --runner codex-ollama --draft-pr

# Continuous watcher for assigned tickets
python3 quarter.py watch --assigned-to minion --runner codex-ollama --draft-pr

# Voice escalation helper
python3 vocal.py --message-file /tmp/vb-escalation.txt
```

Parallel ticket runs use temporary worktrees so multiple PRs can progress at once.
Voice escalations are serialized so two minions do not call the same user at the same time.

Dashboard
                    /

                    Developer Guide

                Vocal Bridge Developer Guide

                    Everything you need to integrate voice agents into your application.

                        Ask the AI Assistant

                        Ask questions about integration, Client Actions, AI Agent mode, CLI commands, or deploy a new agent.

                vocal-bridge assistant

                >
                Hey! I'm the Vocal Bridge assistant. I have access to the full developer guide -- ask me anything about integration, Client Actions, AI Agent mode, the CLI, or how to build a voice-enabled app end to end.

                >
                I can also help you deploy a new voice agent right here if you'd like. What can I help with?

                $

                0/500

                Verify Your Phone Number

                Verify your phone to continue chatting and deploy your agent.

                    By providing your phone number, you consent to receive SMS verification codes. Message and data rates may apply.

                        Sent to .

                        Build Your Voice App in 4 Steps

                        Go from idea to a live Voice UI in under an hour.

                                1

                                    Sign Up

                                    Create your free account.

                                    Sign up

                                2

                                    Get Your API Key

                                    From the dashboard's API Keys tab.

                                    Dashboard

                                3

                                    Copy the Developer Guide

                                    Click "Copy All" below to grab the docs.

                            4

                                Prompt Your Coding Assistant

                                    Paste the docs into Claude Code, Cursor, Codex, Lovable, or Replit and describe what you want to build.

                                claude — ~/my-app

                Overview

                        Vocal Bridge provides voice AI agents that you can integrate into any application using WebRTC.
                        Your users can have real-time voice conversations with AI agents through web browsers, mobile apps,
                        or any platform that supports WebRTC.

                                Real-time Voice

                            Sub-second latency voice AI using WebRTC

                                Secure API Keys

                            Production-ready authentication

                                Multi-platform

                            JavaScript, Python, React, Flutter, and more

                Quick Start

                    Get your voice agent working in 3 steps:

                            1

                                Create an API Key

                                    Go to your agent's page, open Developer Mode, and click "Create API Key" in the API Keys section.

                            2

                                Install the SDK

                                    npm install @vocalbridgeai/sdk

                            3

                                Connect

                                    import { VocalBridge } from '@vocalbridgeai/sdk';

const vb = new VocalBridge({
  auth: { tokenUrl: '/api/voice-token' },
});

vb.on('transcript', ({ role, text }) => {
  console.log(`[${role}] ${text}`);
});

await vb.connect();
// Agent audio plays automatically. Mic is live.

                                    The SDK handles token exchange, WebRTC connections, audio playback, heartbeats, and transcript accumulation automatically.

                            Need more control? See Advanced: Direct WebRTC Integration at the bottom of this guide.

                Authentication

                        Vocal Bridge uses API keys for authentication. API keys allow your backend server to generate
                        access tokens without requiring user login.

                                    Security: Never expose your API key in client-side code. Always call the token endpoint from your backend server.

                    API Key Format

                    API keys start with vb_ followed by a secure random string:

                    vb_abc123def456...

                    Using API Keys

                    Include your API key in requests using either method:

                        # Option 1: X-API-Key header (recommended)
curl -H "X-API-Key: vb_your_api_key" http://vocalbridgeai.com/api/v1/token

# Option 2: Authorization header
curl -H "Authorization: Bearer vb_your_api_key" http://vocalbridgeai.com/api/v1/token

                    Account-Level API Keys

                        Account-level API keys work across all your agents. When using an account-level key, you must include
                        the X-Agent-Id header to specify which agent to target:

                        # Account-level key: include X-Agent-Id header
curl -H "X-API-Key: vb_your_account_key" \
     -H "X-Agent-Id: your-agent-uuid" \
     http://vocalbridgeai.com/api/v1/token

                        Agent-scoped API keys do not require this header — the agent is determined automatically from the key.

                    SDK Auth Strategies

                    The JavaScript SDK supports three authentication strategies:

                        // 1. Token URL (production — recommended)
// Your backend proxies the request, keeping your API key server-side.
{ auth: { tokenUrl: '/api/voice-token' } }

// 2. API Key (prototyping only — exposes key to browser)
{ auth: { apiKey: 'vb_xxx', agentId: 'your-agent-uuid' } }

// 3. Custom provider (maximum flexibility)
{ auth: { tokenProvider: async () => ({ url, token, room_name, ... }) } }

                API Reference

                            POST
                            /api/v1/token

                        Generate a LiveKit access token for connecting to the agent.

                        Request Headers

                                    X-API-Key
                                    Your API key (required)

                                    X-Agent-Id
                                    Agent UUID (required for account-level API keys)

                                    Content-Type
                                    application/json

                        Request Body (optional)

                                    Field
                                    Type
                                    Description

                                    participant_name
                                    string
                                    Display name for the participant (default: "API Client")

                                    session_id
                                    string
                                    Custom session ID (default: auto-generated)

                        Response

                            {
  "livekit_url": "wss://tutor-j7bhwjbm.livekit.cloud",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "room_name": "user-abc-agent-xyz-api-12345",
  "participant_identity": "api-client-xxxx-12345",
  "expires_in": 3600,
  "agent_mode": "cascaded_concierge"
}

                            GET
                            /api/v1/agent

                        Get information about the agent associated with your API key.

                        Response

                            {
  "id": "uuid",
  "name": "My Voice Agent",
  "mode": "cascaded_concierge",
  "deployment_status": "active",
  "phone_number": "+1234567890",
  "greeting": "Hello! How can I help you?",
  "background_enabled": true,
  "hold_enabled": false,
  "hangup_enabled": false,
  "created_at": "2025-01-14T12:00:00Z"
}

                JavaScript SDK

                    The official SDK handles connections, audio, transcripts, and actions with minimal code.

                    Installation

                        npm install @vocalbridgeai/sdk

                    Complete Example

                        import { VocalBridge } from '@vocalbridgeai/sdk';

const vb = new VocalBridge({
  auth: { tokenUrl: '/api/voice-token' },
  participantName: 'User',
  debug: true,
});

// Connection state
vb.on('connectionStateChanged', (state) => {
  console.log('State:', state);
  // disconnected → connecting → waiting_for_agent → connected
});

// Live transcript (automatic — no setup needed)
vb.on('transcript', ({ role, text }) => {
  console.log(`${role === 'user' ? 'You' : 'Agent'}: ${text}`);
});

// Custom agent actions
vb.on('agentAction', ({ action, payload }) => {
  if (action === 'show_product') showProductModal(payload);
});

// Errors
vb.on('error', (err) => {
  console.error(err.code, err.message);
});

// Connect — mic and agent audio are handled automatically
await vb.connect();

// Send actions to the agent
await vb.sendAction('user_clicked_buy', { productId: '123' });

// Mute/unmute
await vb.toggleMicrophone();

// Disconnect
await vb.disconnect();

                    SDK Options

                                    Option
                                    Type
                                    Default
                                    Description

                                authAuthConfigrequiredAuthentication strategy

                                participantNamestring"User"Display name

                                sessionIdstringautoCustom session ID

                                autoAckHeartbeatbooleantrueAuto-acknowledge agent heartbeats

                                autoPlayAudiobooleantrueAuto-play agent audio

                                maxReconnectAttemptsnumber3Max reconnect retries

                                debugbooleanfalseConsole logging

                    SDK Methods

                                    Method
                                    Description

                                connect()Connect to the voice agent

                                disconnect()Disconnect and clean up

                                setMicrophoneEnabled(enabled)Mute/unmute mic

                                toggleMicrophone()Toggle mic state

                                sendAction(action, payload?)Send custom action to agent

                                sendAIAgentResponse(turnId, response)Respond to AI agent query

                                onAIAgentQuery(handler)Register auto-response handler

                                clearTranscript()Clear accumulated transcript

                                on(event, handler)Subscribe to event

                                off(event, handler)Unsubscribe from event

                    SDK Events

                                    Event
                                    Payload
                                    Description

                                connectionStateChangedConnectionStateState transition

                                transcript{ role, text, timestamp }New transcript entry

                                agentAction{ action, payload }Custom agent action

                                heartbeat{ timestamp, agent_identity }Agent heartbeat

                                aiAgentQuery{ query, turnId }AI agent query

                                microphoneChangedbooleanMic state change

                                errorVocalBridgeErrorError occurred

                    SDK Error Codes

                                    Code
                                    When

                                TOKEN_FETCH_FAILEDToken request failed (network, 401, etc.)

                                CONNECTION_FAILEDWebRTC connection failed

                                MICROPHONE_ERRORMic access denied or unavailable

                                DATA_CHANNEL_ERRORFailed to send data to agent

                                RECONNECT_FAILEDAll reconnection attempts exhausted

                                USAGE_LIMIT_EXCEEDED403 from token endpoint

                                AGENT_NOT_FOUND404 — agent ID doesn't exist

                                AGENT_NOT_ACTIVEAgent exists but isn't active

                    Backend Token Endpoint (Node.js/Express)

                        // server.js
const express = require('express');
const app = express();

const VOCAL_BRIDGE_API_KEY = process.env.VOCAL_BRIDGE_API_KEY;

app.get('/api/voice-token', async (req, res) => {
  try {
    const response = await fetch('https://vocalbridgeai.com/api/v1/token', {
      method: 'POST',
      headers: {
        'X-API-Key': VOCAL_BRIDGE_API_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        participant_name: req.user?.name || 'User'
      })
    });

    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Failed to get token:', error);
    res.status(500).json({ error: 'Failed to get voice token' });
  }
});

app.listen(3000);

                    Next.js API Route Example

                    Create app/api/voice-token/route.ts:

                        // app/api/voice-token/route.ts (Next.js App Router)
import { NextRequest, NextResponse } from 'next/server';

const VOCAL_BRIDGE_API_KEY = process.env.VOCAL_BRIDGE_API_KEY!;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch('https://vocalbridgeai.com/api/v1/token', {
      method: 'POST',
      headers: {
        'X-API-Key': VOCAL_BRIDGE_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        participant_name: body.participant_name || 'Web User',
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to get token');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to get voice token' },
      { status: 500 }
    );
  }
}

                Python SDK

                    Use the LiveKit Python SDK for server-side or desktop applications.

                    Installation

                        pip install livekit requests

                    Complete Example

                        import asyncio
import os
import requests
from livekit import rtc

VOCAL_BRIDGE_API_KEY = os.environ.get('VOCAL_BRIDGE_API_KEY')
VOCAL_BRIDGE_URL = 'http://vocalbridgeai.com'

def get_voice_token(participant_name: str = 'Python Client'):
    """Get a voice token from Vocal Bridge API."""
    response = requests.post(
        f'{VOCAL_BRIDGE_URL}/api/v1/token',
        headers={
            'X-API-Key': VOCAL_BRIDGE_API_KEY,
            'Content-Type': 'application/json'
        },
        json={'participant_name': participant_name}
    )
    response.raise_for_status()
    return response.json()

async def main():
    # Get token
    token_data = get_voice_token()
    print(f"Connecting to room: {token_data['room_name']}")

    # Create room
    room = rtc.Room()

    # Set up event handlers
    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print("Agent audio connected!")
            # Process audio stream
            audio_stream = rtc.AudioStream(track)
            # ... handle audio frames

    @room.on("disconnected")
    def on_disconnected():
        print("Disconnected from room")

    # Connect
    await room.connect(token_data['livekit_url'], token_data['token'])
    print(f"Connected! Room: {room.name}")

    # Publish microphone (requires audio input device)
    source = rtc.AudioSource(sample_rate=48000, num_channels=1)
    track = rtc.LocalAudioTrack.create_audio_track("microphone", source)
    await room.local_participant.publish_track(track)
    print("Microphone enabled - start speaking!")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await room.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

                    Flask Backend Example

                        # app.py
from flask import Flask, jsonify
import requests
import os

app = Flask(__name__)

VOCAL_BRIDGE_API_KEY = os.environ.get('VOCAL_BRIDGE_API_KEY')
VOCAL_BRIDGE_URL = 'http://vocalbridgeai.com'

@app.route('/api/voice-token')
def get_voice_token():
    response = requests.post(
        f'{VOCAL_BRIDGE_URL}/api/v1/token',
        headers={
            'X-API-Key': VOCAL_BRIDGE_API_KEY,
            'Content-Type': 'application/json'
        },
        json={'participant_name': 'Web User'}
    )
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(port=5000)

                React Integration

                    The React SDK provides purpose-built hooks for voice agent integration.

                    Installation

                        npm install @vocalbridgeai/sdk @vocalbridgeai/react

                    Complete Example

                        import { VocalBridgeProvider, useVocalBridge, useTranscript, useAgentActions, useAIAgent } from '@vocalbridgeai/react';
import { ConnectionState } from '@vocalbridgeai/sdk';

function App() {
  return (
    <VocalBridgeProvider options={{ auth: { tokenUrl: '/api/voice-token' } }}>
      <VoiceChat />
    </VocalBridgeProvider>
  );
}

function VoiceChat() {
  const { state, connect, disconnect, isMicrophoneEnabled, toggleMicrophone, error } = useVocalBridge();
  const { transcript } = useTranscript();
  const { onAction, sendAction } = useAgentActions();

  // Handle agent actions
  useEffect(() => {
    return onAction('show_product', (payload) => {
      showProductModal(payload);
    });
  }, [onAction]);

  // AI Agent integration (automatic mode)
  useAIAgent({
    onQuery: async (query) => {
      return await myAgent.ask(query);
    },
  });

  return (
    <div>
      <p>Status: {state}</p>
      {error && <p style={{ color: 'red' }}>{error.message}</p>}

      {state === ConnectionState.Disconnected ? (
        <button onClick={connect}>Start Voice Chat</button>
      ) : (
        <>
          <button onClick={disconnect}>End Call</button>
          <button onClick={toggleMicrophone}>
            {isMicrophoneEnabled ? 'Mute' : 'Unmute'}
          </button>
        </>
      )}

      {transcript.map((entry, i) => (
        <p key={i}>
          <strong>{entry.role === 'user' ? 'You' : 'Agent'}:</strong> {entry.text}
        </p>
      ))}
    </div>
  );
}

                    React Hooks Reference

                    <VocalBridgeProvider>

                    Wraps your app and manages the SDK lifecycle. Disconnects automatically on unmount.

                    useVocalBridge()

                    Primary hook for connection lifecycle, mic control, and sending actions.

                        const {
  state,                // ConnectionState
  connect,              // () => Promise<void>
  disconnect,           // () => Promise<void>
  isMicrophoneEnabled,  // boolean
  toggleMicrophone,     // () => Promise<void>
  setMicrophoneEnabled, // (enabled: boolean) => Promise<void>
  sendAction,           // (action: string, payload?: object) => Promise<void>
  agentMode,            // string | undefined
  error,                // VocalBridgeError | null
  client,               // VocalBridge instance (advanced)
} = useVocalBridge();

                    useTranscript()

                    Live conversation transcript. Updates automatically on every new entry.

                        const { transcript, clear } = useTranscript();
// transcript: Array<{ role: 'user' | 'agent', text: string, timestamp: number }>

                    useAgentActions()

                    Bidirectional custom actions.

                        const { lastAction, sendAction, onAction } = useAgentActions();

// Per-action handler with auto-cleanup
useEffect(() => {
  return onAction('show_product', (payload) => {
    setProduct(payload);
  });
}, [onAction]);

// Send action to agent
sendAction('user_clicked_buy', { productId: '123' });

                    useAIAgent()

                    AI Agent integration with automatic or manual response flow.

                        // Automatic (callback):
useAIAgent({
  onQuery: async (query) => {
    return await myAgent.ask(query); // auto-responds
  },
});

// Manual:
const { pendingQuery, respond } = useAIAgent();

useEffect(() => {
  if (pendingQuery) {
    myAgent.ask(pendingQuery.query).then(answer => {
      respond(pendingQuery.turnId, answer);
    });
  }
}, [pendingQuery]);

                    Next.js API Route Example

                    Create app/api/voice-token/route.ts:

                        // app/api/voice-token/route.ts (Next.js App Router)
import { NextRequest, NextResponse } from 'next/server';

const VOCAL_BRIDGE_API_KEY = process.env.VOCAL_BRIDGE_API_KEY!;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch('https://vocalbridgeai.com/api/v1/token', {
      method: 'POST',
      headers: {
        'X-API-Key': VOCAL_BRIDGE_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        participant_name: body.participant_name || 'Web User',
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to get token');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to get voice token' },
      { status: 500 }
    );
  }
}

                Flutter SDK

                    Use the LiveKit Flutter SDK to build voice-enabled mobile apps for iOS and Android.

                    Installation

                    Add to your pubspec.yaml:

                        dependencies:
  livekit_client: ^2.3.0
  http: ^1.2.0

                    Complete Example

                        import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:livekit_client/livekit_client.dart';

class VoiceAgentService {
  Room? _room;
  EventsListener<RoomEvent>? _listener;

  // Get token from your backend (recommended for production)
  // Your backend should call Vocal Bridge API with your API key
  Future<Map<String, dynamic>> _getTokenFromBackend() async {
    final response = await http.get(
      Uri.parse('https://your-backend.com/api/voice-token'),
    );
    return jsonDecode(response.body);
  }

  // Alternative: Call Vocal Bridge API directly (for testing/prototyping only)
  // WARNING: Never expose API keys in production mobile apps!
  Future<Map<String, dynamic>> _getTokenDirect(String apiKey) async {
    final response = await http.post(
      Uri.parse('http://vocalbridgeai.com/api/v1/token'),
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'participant_name': 'Mobile User'}),
    );
    return jsonDecode(response.body);
  }

  // Connect to the voice agent
  Future<void> connect() async {
    // Use _getTokenFromBackend() in production
    final tokenData = await _getTokenFromBackend();
    final livekitUrl = tokenData['livekit_url'] as String;
    final token = tokenData['token'] as String;

    _room = Room();

    // Listen for agent audio
    _listener = _room!.createListener();
    _listener!.on<TrackSubscribedEvent>((event) {
      if (event.track.kind == TrackType.AUDIO) {
        // Audio is automatically played by LiveKit SDK
        print('Agent audio track subscribed');
      }
    });

    // Handle connection state
    _listener!.on<RoomDisconnectedEvent>((event) {
      print('Disconnected from room');
    });

    // Connect to the room
    await _room!.connect(livekitUrl, token);
    print('Connected to room: ${_room!.name}');

    // Enable microphone
    await _room!.localParticipant?.setMicrophoneEnabled(true);
    print('Microphone enabled - start speaking!');
  }

  // Disconnect from the agent
  Future<void> disconnect() async {
    await _room?.disconnect();
    _room = null;
    _listener = null;
  }

  // Check if connected
  bool get isConnected => _room?.connectionState == ConnectionState.connected;
}

// Usage in a Flutter widget
class VoiceAgentButton extends StatefulWidget {
  @override
  _VoiceAgentButtonState createState() => _VoiceAgentButtonState();
}

class _VoiceAgentButtonState extends State<VoiceAgentButton> {
  final _voiceAgent = VoiceAgentService();
  bool _isConnecting = false;

  Future<void> _toggleConnection() async {
    setState(() => _isConnecting = true);
    try {
      if (_voiceAgent.isConnected) {
        await _voiceAgent.disconnect();
      } else {
        await _voiceAgent.connect();
      }
    } finally {
      setState(() => _isConnecting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: _isConnecting ? null : _toggleConnection,
      child: Text(_isConnecting
          ? 'Connecting...'
          : _voiceAgent.isConnected
              ? 'End Call'
              : 'Start Voice Chat'),
    );
  }
}

                    Handling Client Actions (Flutter)

                        // Add to VoiceAgentService class

// Handle actions from the agent
void _setupClientActionHandler() {
  _listener!.on<DataReceivedEvent>((event) {
    if (event.topic == 'client_actions') {
      final data = jsonDecode(utf8.decode(event.data));
      if (data['type'] == 'client_action') {
        _handleAgentAction(data['action'], data['payload']);
      }
    }
  });
}

void _handleAgentAction(String action, Map<String, dynamic> payload) {
  switch (action) {
    case 'navigate':
      // Navigate to a screen
      print('Navigate to: ${payload['screen']}');
      break;
    case 'show_product':
      // Show a product card
      print('Show product: ${payload['productId']}');
      break;
    default:
      print('Unknown action: $action');
  }
}

// Send actions to the agent
Future<void> sendActionToAgent(String action, [Map<String, dynamic>? payload]) async {
  final message = jsonEncode({
    'type': 'client_action',
    'action': action,
    'payload': payload ?? {},
  });
  await _room?.localParticipant?.publishData(
    utf8.encode(message),
    reliable: true,
    topic: 'client_actions',
  );
}

// Example: Notify agent that user tapped a button
// await sendActionToAgent('button_tapped', {'buttonId': 'buy_now'});

                    Platform Setup

                        iOS Configuration

                        Add to ios/Runner/Info.plist:

                            <key>NSMicrophoneUsageDescription</key>
<string>This app needs microphone access for voice chat</string>
<key>UIBackgroundModes</key>
<array>
  <string>audio</string>
</array>

                        Android Configuration

                        Add to android/app/src/main/AndroidManifest.xml:

                            <uses-permission android:name="android.permission.RECORD_AUDIO"/>
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS"/>

                Client Actions

                        Client Actions enable bidirectional communication between your voice agent and your client application
                        via LiveKit's data channel.

                    Directions

                        Agent to App: The agent triggers actions in your client (e.g., navigate to a page, show a product card, update the UI).

                        App to Agent: Your client sends events to the agent (e.g., user clicked a button, form submitted, data loaded).

                    Behavior (App to Agent)

                    Each app_to_agent action has a behavior that controls how the agent handles the inbound event:

                        respond (default): The agent generates a reply when this event arrives. Use for events that require the agent to speak.

                        notify: The event is silently added to conversation context. The agent sees it on its next turn but does not reply immediately. Use for informational updates.

                        This prevents feedback loops where an agent action triggers a client event which triggers another agent reply, and so on.

                    How It Works

                            Agent to App (Outbound)

                                Agent decides to trigger an action during conversation

                                Agent calls trigger_client_action

                                Action is published to LiveKit data channel

                                Your app receives and handles it

                            App to Agent (Inbound)

                                Your app publishes data to LiveKit

                                Agent receives and validates the event

                                Behavior is checked: respond or notify

                                Agent replies or silently absorbs the event

                    Using the SDK

                        import { VocalBridge } from '@vocalbridgeai/sdk';

const vb = new VocalBridge({ auth: { tokenUrl: '/api/voice-token' } });

// Receive actions from agent
vb.on('agentAction', ({ action, payload }) => {
  switch (action) {
    case 'navigate':
      window.location.href = payload.url;
      break;
    case 'show_product':
      showProductModal(payload.product_id);
      break;
    default:
      console.log('Unknown action:', action, payload);
  }
});

// Send actions to agent
await vb.sendAction('user_clicked_buy', { productId: '123', quantity: 2 });

// Notify (behavior configured on agent side)
await vb.sendAction('practice_result', { score: 95, word: 'hello' });

                    React

                        const { onAction, sendAction } = useAgentActions();

useEffect(() => {
  return onAction('show_product', (payload) => {
    setProduct(payload);
  });
}, [onAction]);

// Send action
<button onClick={() => sendAction('user_clicked_buy', { productId: '123' })}>
  Buy Now
</button>

                    Example Configuration

                    When configuring your agent, you can add client actions like:

                                    Action Name
                                    Direction
                                    Behavior
                                    Description

                                    show_product
                                    agent_to_app
                                    —
                                    Display product details in the app

                                    user_clicked_buy
                                    app_to_agent
                                    respond
                                    User clicked the buy button

                                    practice_result
                                    app_to_agent
                                    notify
                                    User completed a practice exercise

                    Configure via CLI

                    Save your client actions to a JSON file and use the CLI:

                    # Set client actions from file
vb config set --client-actions-file client_actions.json

# Example client_actions.json:
# [
#   {"name": "show_product", "description": "Display a product card", "direction": "agent_to_app"},
#   {"name": "user_clicked_buy", "description": "User clicked buy", "direction": "app_to_agent", "behavior": "respond"},
#   {"name": "practice_result", "description": "Practice completed", "direction": "app_to_agent", "behavior": "notify"}
# ]

                Live Transcript (Built-in)

                        All Vocal Bridge agents automatically send a send_transcript event
                        whenever the user speaks or the agent responds. This is a built-in protocol-level feature that works independently
                        of any configured client actions — no setup required.

                    Transcript Message Format

                        {
  "type": "client_action",
  "action": "send_transcript",
  "payload": {
    "role": "user",       // "user" or "agent"
    "text": "Hello, how are you?",
    "timestamp": 1708123456789  // Epoch milliseconds
  }
}

                    Using the SDK

                        const vb = new VocalBridge({ auth: { tokenUrl: '/api/voice-token' } });

// Transcript events arrive automatically
vb.on('transcript', ({ role, text, timestamp }) => {
  console.log(`${role === 'user' ? 'You' : 'Agent'}: ${text}`);
});

// Access the full conversation history at any time
console.log(vb.transcript);

// Clear transcript
vb.clearTranscript();

                    React

                        const { transcript, clear } = useTranscript();

return (
  <div>
    {transcript.map((entry, i) => (
      <p key={i}>
        <strong>{entry.role === 'user' ? 'You' : 'Agent'}:</strong> {entry.text}
      </p>
    ))}
    <button onClick={clear}>Clear</button>
  </div>
);

                    Flutter Example

                        import 'dart:convert';
import 'package:livekit_client/livekit_client.dart';

class TranscriptEntry {
  final String role;
  final String text;
  final int timestamp;
  TranscriptEntry({required this.role, required this.text, required this.timestamp});
}

// In your room setup:
final transcript = <TranscriptEntry>[];

listener.on<DataReceivedEvent>((event) {
  if (event.topic == 'client_actions') {
    final data = jsonDecode(utf8.decode(event.data));
    if (data['type'] == 'client_action' && data['action'] == 'send_transcript') {
      final payload = data['payload'];
      transcript.add(TranscriptEntry(
        role: payload['role'],
        text: payload['text'],
        timestamp: payload['timestamp'],
      ));
      // Update UI via setState or stream controller
    }
  }
});

                                How It Works

                                    Transcript events are sent on the same client_actions data channel topic as heartbeat and client actions

                                    User transcripts are sent when speech-to-text produces a final transcription

                                    Agent transcripts are sent when the agent produces a response

                                    No configuration needed — this is automatic for all agents

                    Listener Mode

                    Passive observer

                        Listener mode is a passive-observer Vocal Bridge agent: it joins
                        the room, transcribes multi-speaker audio with speaker diarization, and streams
                        coaching suggestions to your app via the data channel. It never speaks.
                        Use it for live coaching during multi-party conversations — investor calls,
                        sales calls, interviews — where the user needs guidance in real time.

                        Create one with vb agent create --style Listener
                        or pick "Listener" in the agent-creation dashboard.

                        Three built-in actions arrive on the client_actions
                        topic. You don't configure these — they're always sent when an agent is in this mode.

                    live_transcript

                        Fires for both interim (is_final: false) and final
                        (is_final: true) transcript segments.
                        Interims arrive continuously while a speaker is talking and represent the current best guess
                        at what's been said so far; each interim replaces the prior one for that utterance.
                        Finals arrive when an utterance ends, lock in the text, and are the only transcripts that
                        carry a reliable speaker_id. Group consecutive
                        same-speaker finals into one visual block — start a new block when
                        speaker_id changes.

                        {
  "type": "client_action",
  "action": "live_transcript",
  "payload": {
    "speaker_id": "S0",         // null for interims; "S0"/"S1"/... or "unknown" for finals
    "text": "...",               // current transcript (interim) or finalized text
    "is_final": true,
    "timestamp": 1708123456789
  }
}

                    coaching_suggestion

                        Fires when the latest turn matches the coaching policy you defined in your
                        custom_prompt. Guidance is grounded in any MCP
                        servers you've configured on the agent, and (if web search is enabled) in live web results.
                        Rate-limited so cards don't pile up mid-question: at most one coaching response is in flight
                        at a time, with a short cooldown between deliveries — your UI can size for roughly one
                        card every few seconds, not a card per transcript segment.

                        The guidance field is Markdown — render
                        with any Markdown renderer. Your custom_prompt
                        controls what shape the Markdown takes (headlines, bullets, tables, etc.); the
                        platform only enforces brevity, not structure.

                        {
  "type": "client_action",
  "action": "coaching_suggestion",
  "payload": {
    "speaker_id": "S0",
    "question_text": "What was your Q3 margin?",      // the turn that triggered the coach
    "guidance": "**Lead with:** Margins expanded 120bps YoY...",  // Markdown
    "format": "markdown",
    "timestamp": 1708123456789,
    "job_id": "..."
  }
}

                    speaker_map_update

                        Fires periodically as the conversation progresses, with an inferred mapping from raw
                        speaker IDs to names/roles based on what's been said (e.g. self-introductions, references
                        to each other). The mapping is a suggestion, not authoritative — your UI can
                        use it to upgrade S0 →
                        "Jane Doe (Morgan Stanley)", ignore it, or let
                        the user override. Expect the mapping to refine over the course of the session as more
                        context accumulates.

                        {
  "type": "client_action",
  "action": "speaker_map_update",
  "payload": {
    "mapping": {
      "S0": {"name": "Jane Doe", "org": "Morgan Stanley", "role": "analyst", "confidence": 0.9},
      "S1": {"name": null, "org": null, "role": "executive", "confidence": 0.4}
    },
    "timestamp": 1708123456789
  }
}

                    Subscribing (JavaScript SDK)

                        All three listener actions arrive on the SDK's
                        agentAction event.

                        import { VocalBridge } from '@vocalbridgeai/sdk';

const vb = new VocalBridge({
  auth: { tokenUrl: '/api/voice-token' },
});

vb.on('agentAction', ({ action, payload }) => {
  switch (action) {
    case 'live_transcript': {
      const { speaker_id, text, is_final } = payload;
      if (is_final) appendFinal(speaker_id, text);
      else updateInterim(text);
      break;
    }
    case 'coaching_suggestion':
      // payload.guidance is Markdown — render with any Markdown renderer.
      renderCoachingCard(payload);
      break;
    case 'speaker_map_update':
      // payload.mapping is { S0: {name, org, role, confidence}, ... }
      refreshSpeakerLabels(payload.mapping);
      break;
  }
});

vb.on('error', (err) => console.error(err.code, err.message));

// Connect — the SDK publishes the user's microphone automatically.
await vb.connect();

                    Subscribing (React SDK)

                        import { useAgentActions } from '@vocalbridgeai/react';

function ListenerUI() {
  useAgentActions((action, payload) => {
    if (action === 'live_transcript') {
      const { speaker_id, text, is_final } = payload;
      if (is_final) appendFinal(speaker_id, text);
      else updateInterim(text);
    } else if (action === 'coaching_suggestion') {
      renderCoachingCard(payload);
    } else if (action === 'speaker_map_update') {
      refreshSpeakerLabels(payload.mapping);
    }
  });

  return <YourTranscriptAndCoachingPanels />;
}

                    Settings

                        Tune coaching behavior via these model settings. All are optional with sensible defaults — set just the ones you care about.

                                    Setting
                                    Range
                                    Default
                                    What it does

                                    coaching.coachee_description
                                    text, ≤ 500 chars
                                    empty
                                    Names the person you're coaching. When set, the agent only generates a coaching card when someone else is speaking (so it doesn't try to coach this person on their own words), and tailors each card as guidance for them. Example: "the CFO during earnings Q&A".

                                    coaching.debounce_seconds
                                    0–60
                                    12
                                    Minimum seconds between coaching cards. Higher = fewer, more spaced-out suggestions.

                                    coaching.context_turns
                                    0–50
                                    10
                                    How many recent turns of conversation the agent considers per coaching card.

                                    coaching.job_timeout_seconds
                                    5–120
                                    30
                                    Maximum seconds to wait for each coaching card before giving up.

                                    coaching.gate_enabled
                                    true / false
                                    true
                                    When On, coaching only appears when the conversation matches the trigger conditions in your prompt. When Off, every spoken turn produces a coaching card.

                                    speaker_map.enabled
                                    true / false
                                    true
                                    When On, the agent identifies who's speaking and emits speaker_map_update events. When Off, your app only sees raw labels like S0, S1.

                                    speaker_map.update_interval_seconds
                                    5–300
                                    20
                                    How often the agent re-checks for new speaker identities.

                    Set them via the CLI:

                        vb config set --coachee-description "the CFO during earnings Q&A" \
              --coaching-debounce 8 \
              --coaching-gate true

# Or at create time:
vb agent create --name "IR Coach" --style Listener \
                --prompt "..." \
                --coachee-description "the company CFO"

                        Run vb config options to see the live schema with current values for your agent.

                    Writing the system prompt

                        Your custom_prompt drives both when
                        the agent emits a coaching suggestion and what it says — be explicit about both.
                        Example skeleton:

                        You are an IR coach for the CFO during earnings Q&A.

TRIGGER ON: an analyst asks a substantive financial question.
SKIP: small talk, acknowledgements, partial / mid-thought utterances.

When triggered, respond in this Markdown shape:
**Recommended answer:** <one bold line the CFO can lead with>
- <supporting point 1, starting with a **key term**>
- <supporting point 2>
*<one-line caveat — what NOT to say>*

Keep the entire response under 60 words.

                        Grounding data (filings, transcripts, market data, knowledge base) should come from an
                        MCP server you configure on the agent — the coach calls retrieval tools on demand
                        per turn instead of stuffing context into the prompt.

                                Audio input

                                    The SDK handles audio capture automatically — calling
                                    vb.connect() publishes the user's
                                    microphone. Whatever the mic picks up is what the listener transcribes. For
                                    multi-speaker audio (a conference call playing through speakers, a virtual
                                    audio-loopback device), ensure the OS-level input source is correct and the
                                    input volume isn't clipping.

                MCP Tools

                        The Model Context Protocol (MCP) allows your voice agent to connect to external tools and services.
                        By providing an MCP server URL, your agent gains access to calendars, email, CRM systems, databases,
                        and thousands of other integrations.

                                Quick Setup with Zapier

                                    The easiest way to add tools is through Zapier MCP.
                                    Connect 7,000+ apps to your voice agent in minutes.

                    How MCP Works

                        Obtain an MCP server URL from Zapier or your own MCP server

                        Add the URL in your agent's configuration

                        The agent automatically discovers and loads available tools

                        During conversations, the agent can call these tools to fetch data or perform actions

                    Example Use Cases

                                Calendar Integration

                            Check availability, book appointments, send meeting invites via Google Calendar or Outlook

                                CRM Access

                            Look up customer info, create leads, update contact records in Salesforce, HubSpot, etc.

                                Email & Messaging

                            Send emails, Slack messages, or SMS notifications during or after calls

                                Database Queries

                            Query product catalogs, inventory, order status, or any custom database

                    Getting an MCP Server URL

                        Option 1: Zapier MCP (Recommended)

                            Go to zapier.com/mcp

                            Sign in and configure the apps you want to connect

                            Copy your MCP server URL (format: https://actions.zapier.com/mcp/...)

                            Paste into your agent's MCP Server URL field

                        Option 2: Custom MCP Server

                        Build your own MCP server using the MCP specification. Your server must support the Streamable HTTP transport.

                    Viewing Available Tools

                        After adding an MCP server URL to your agent, the available tools will be displayed in the agent's
                        configuration page. The agent will automatically use these tools when relevant during conversations.

                Custom HTTP API Tools

                        Custom HTTP API tools let your agent call external REST APIs during conversations. The agent
                        can fetch data, submit forms, trigger webhooks, or interact with any HTTPS endpoint. Tools
                        run in the background and results are spoken back to the caller.

                    How It Works

                        Configure one or more API tools with URL, method, authentication, and parameters

                        During a conversation, the agent decides when to call a tool based on the user's request

                        The agent constructs the HTTP request, injects authentication, and calls the endpoint

                        The response is parsed and the agent speaks the result to the caller

                    Supported Features

                            HTTP Methods

                            GET, POST, PUT, DELETE, PATCH

                            Authentication

                            Bearer token, Basic auth, Custom header, Query parameter, or None

                            Parameters

                            Query params, path params, and request body. Types: string, number, boolean

                            Reliability

                            Configurable timeout (1-300s) and retry count (0-5). Auto-retry on server errors

                    Example Configuration

                    Each tool is defined as a JSON object with the following fields:

                    [
  {
    "id": "1",
    "name": "get_weather",
    "description": "Get the current weather for a city",
    "method": "GET",
    "url": "https://api.weather.com/v1/current",
    "auth": {
      "type": "bearer",
      "credentials": { "token": "your-api-key" }
    },
    "parameters": [
      {
        "name": "city",
        "type": "string",
        "description": "City name",
        "required": true,
        "location": "query"
      }
    ],
    "timeout": 30,
    "max_retries": 2,
    "enabled": true
  }
]

                    Authentication Types

                                    Type
                                    Credentials
                                    Behavior

                                    bearer
                                    {"token": "sk-xxx"}
                                    Sends Authorization: Bearer sk-xxx

                                    basic
                                    {"username": "u", "password": "p"}
                                    Sends Base64-encoded Basic auth header

                                    header
                                    {"header_name": "X-Key", "header_value": "val"}
                                    Sends a custom HTTP header

                                    query
                                    {"param_name": "key", "param_value": "val"}
                                    Appends a query parameter to the URL

                                    none
                                    N/A
                                    No authentication

                    Configure via CLI

                    Save your tools to a JSON file and use the CLI to update your agent:

                    # Set API tools from file
vb config set --api-tools-file api_tools.json

# Clear all API tools
vb config set --api-tools-file /dev/stdin <<< '[]'

# View current tools
vb config show

                    Limits

                        Maximum 20 tools per agent

                        Tool names must be unique, start with a letter, and contain only letters, numbers, and underscores

                        URLs must use HTTPS only

                        Credentials are encrypted at rest

                Post-Processing

                        Post-processing runs automatically after each call ends. Use it to summarize conversations,
                        update CRM records, send follow-up emails, create tickets, or trigger any workflow based on
                        what happened during the call.

                                Automatic Execution

                                    Post-processing runs in the background after every call. No user action required.
                                    The transcript and call metadata are automatically available.

                    How It Works

                        Call ends (user hangs up or agent ends the call)

                        Full conversation transcript is captured

                        Post-processing LLM analyzes the transcript using your custom prompt

                        If MCP tools are configured, the LLM can call them to perform actions

                        Results are logged for review

                    Configuration Options

                            Post-Processing Prompt

                                Tell the LLM what to do with the conversation transcript. Be specific about the output format
                                and actions to take.

                                Example: "Analyze this call transcript and: 1) Create a brief summary (2-3 sentences),
                                2) Extract any action items mentioned, 3) Identify the caller's sentiment (positive/neutral/negative),
                                4) If the caller requested a callback, create a task in the CRM."

                            Post-Processing MCP Server

                                Optionally connect a separate MCP server specifically for post-processing tasks.
                                This allows the post-processing LLM to update CRMs, send emails, create tickets,
                                or trigger any automation after the call.

                    Example Use Cases

                                Call Summaries

                            Generate structured summaries with key points, decisions, and next steps

                                CRM Updates

                            Automatically log call notes, update lead status, or create follow-up tasks

                                Follow-up Emails

                            Send personalized follow-up emails based on the conversation content

                                Escalation Alerts

                            Detect urgent issues and notify team members via Slack, email, or SMS

                    Available Context

                    The post-processing LLM has access to:

                        Full transcript - Complete conversation with speaker labels

                        Call duration - How long the call lasted

                        Timestamp - When the call started and ended

                        Agent configuration - The agent's system prompt and settings

                        MCP tools - Any tools configured for post-processing

                AI Agents

                        Connect your existing AI agent to a Vocal Bridge voice agent. The voice agent handles conversation flow, greetings, and filler while delegating domain-specific questions to your agent via the client-side data channel.

                    How It Works

                        User asks a domain-specific question

                        Voice agent sends a query_agent action via the data channel

                        Your app receives the query and forwards it to your AI agent

                        Your app sends the response back via agent_response action

                        Voice agent speaks the response to the user

                    Data Channel Protocol

                    Query from voice agent (Agent to App):

                    {
  "type": "client_action",
  "action": "query_agent",
  "payload": { "query": "What appointments do I have?", "turn_id": "abc123" }
}

                    Response from your agent (App to Agent):

                    {
  "type": "client_action",
  "action": "agent_response",
  "payload": { "response": "You have a dentist at 10am.", "turn_id": "abc123" }
}

                    Using the SDK (Recommended)

                    Automatic mode — SDK handles the response flow:

                    const vb = new VocalBridge({ auth: { tokenUrl: '/api/voice-token' } });

vb.onAIAgentQuery(async (query) => {
  const response = await myAgent.ask(query);
  return response; // Return value is automatically sent back
});

await vb.connect();

                    Manual mode — full control over the response:

                    vb.on('aiAgentQuery', async ({ query, turnId }) => {
  const answer = await myAgent.ask(query);
  vb.sendAIAgentResponse(turnId, answer);
});

                    React

                    Automatic:

                    useAIAgent({
  onQuery: async (query) => await myAgent.ask(query),
});

                    Manual:

                    const { pendingQuery, respond } = useAIAgent();

useEffect(() => {
  if (pendingQuery) {
    myAgent.ask(pendingQuery.query).then(answer => {
      respond(pendingQuery.turnId, answer);
    });
  }
}, [pendingQuery]);

                    Configure via CLI

                    # Enable with inline flags
vb config set --ai-agent-enabled true --ai-agent-description "Customer support agent"

# Or set from a JSON file
vb config set --ai-agent-file ai_agent.json

# Disable
vb config set --ai-agent-enabled false

# View current config
vb config show

                    Configuration

                    {
  "enabled": true,
  "description": "Customer support agent for Acme Corp",
  "verbatim": false
}

                        enabled - Whether AI Agent integration is active

                        description - What your agent does (max 2000 chars). Guides the voice agent on when to delegate.

                        verbatim - If true, speaks responses exactly as received. If false (default), adapts for natural voice delivery.

                    Notes

                        The voice agent fills naturally while waiting for your agent's response (same as background AI)

                        Timeout is 60 seconds — if your agent doesn't respond, the voice agent answers from its own knowledge

                        Works with web deploy targets only (requires data channel)

                Troubleshooting

                            Connection fails with "403 Forbidden"

                                Your API key may be invalid or revoked. Check that you're using the correct API key and that
                                it hasn't been revoked in the dashboard.

                            No audio from the agent

                                If using the SDK, audio is handled automatically. Make sure autoPlayAudio is not set to false.
                                Some browsers require a user gesture (click/tap) before audio can play — ensure connect() is called from a user interaction handler.

                            Microphone not working

                                The browser may not have microphone permissions. The SDK requests permissions automatically during connect().
                                If it fails, you'll get a MICROPHONE_ERROR event:

                                vb.on('error', (err) => {
  if (err.code === 'MICROPHONE_ERROR') {
    alert('Please allow microphone access');
  }
});

                            Token expired

                                Tokens are valid for 1 hour. If you get a token expiration error, call disconnect() and connect()
                                again — the SDK will fetch a fresh token automatically.

                            CORS errors

                                Don't call the Vocal Bridge API directly from the browser. Use the tokenUrl auth strategy
                                with a backend endpoint, or the tokenProvider strategy. This avoids CORS issues and keeps your API key secure.

                CLI

                        The vb CLI lets you manage voice agents from the terminal. View call logs, update prompts,
                        stream debug events, and iterate on your agent without opening the dashboard.

                    Installation

                        pip install vocal-bridge

                    Requires Python 3.9+. Includes WebSocket support for real-time debug streaming.

                    Authentication

                    Authenticate with an agent or account API key:

                        # Interactive login
vb auth login

# Or provide key directly
vb auth login vb_your_api_key_here

# For account keys, select an agent after login
vb agent use

# Check status
vb auth status

                        Get an agent API key from your agent's detail page,
                        or create an account API key from the dashboard's "API Keys" tab.

                    Commands

                                    Command
                                    Description

                                    vb agent
                                    Show current agent info

                                    vb agent list
                                    List all agents

                                    vb agent use
                                    Select an agent to work with

                                    vb agent create
                                    Create and deploy a new agent (Pilot only)

                                    vb logs
                                    List recent call logs

                                    vb logs show <id>
                                    View call details and transcript

                                    vb logs download <id>
                                    Download call recording

                                    vb stats
                                    Show call statistics

                                    vb prompt show
                                    View current prompt and greeting

                                    vb prompt edit
                                    Edit prompt in $EDITOR

                                    vb prompt set --file
                                    Set prompt from file or stdin

                                    vb config show
                                    View all agent settings

                                    vb config get <section>
                                    Export a config section as JSON

                                    vb config edit
                                    Edit full config in $EDITOR (JSON)

                                    vb config set
                                    Update individual settings

                                    vb config options
                                    Discover valid values for settings

                                    vb call <phone>
                                    Place an outbound call (Pilot only)

                                    vb eval <session_id>
                                    Evaluate a call recording with a multimodal LLM (Pilot only, 100/day)

                                    vb debug
                                    Stream real-time debug events

                                    vb docs
                                    Get developer integration docs

                    Discover Valid Options

                    Before updating settings, check what values are available for your agent's style:

                        # Show all available options
vb config options

# Show options for a specific setting
vb config options voice
vb config options "TTS Model"
vb config options language

# Show all settings in a category
vb config options stt
vb config options audio

                    Update Settings

                        # Change agent style
vb config set --style Chatty

# Enable capabilities
vb config set --debug-mode true
vb config set --hold-enabled true

# Set session limits
vb config set --max-call-duration 15
vb config set --max-history-messages 50

# Continuous speech ("keep talking") — agent keeps going on its own after a short
# silence instead of waiting each turn. Great for tutors, narrators, and guided
# experiences. It keeps talking even while it's working in the background (e.g.
# looking something up), and shares the result as soon as it's ready — no dead air.
# The only thing that stops it is the user speaking, so they can interrupt anytime.
vb config set --continuous-mode true
vb config set --continuous-mode true --continuous-mode-delay 3
vb config set --continuous-mode false

# Set integrations from files
vb config set --mcp-servers-file servers.json
vb config set --client-actions-file actions.json
vb config set --api-tools-file tools.json

                            Continuous mode & background work. With continuous mode on, the agent
                            holds the floor and keeps talking on its own — even while it's looking something up or
                            waiting on an integration in the background. It won't go quiet to wait for the user, and it
                            delivers any background result the moment it's ready. The user can always take over simply by
                            speaking. Use --continuous-mode-delay (seconds) to tune how
                            long a pause it waits out before continuing. With continuous mode off (the default), the agent
                            takes turns normally and stays quiet while the user is thinking or waiting on a result.

                    Export & Update Settings (Roundtrip)

                    Export current settings, edit them, and apply changes — updating only what you need:

                        # Export a config section as JSON
vb config get model-settings
vb config get client-actions
vb config get mcp-servers
vb config get api-tools
vb config get ai-agent
vb config get builtin-tools

# Roundtrip: export, edit, and re-apply
vb config get model-settings > settings.json
# edit settings.json...
vb config set --model-settings-file settings.json

# Partial update: change only specific fields with --merge
echo '{"realtime": {"model": "gpt-realtime-2"}}' > update.json
vb config set --model-settings-file update.json --merge

                    Evaluate a Call (Pilot Subscribers)

                        Run a multimodal evaluation of a recorded call session. The full audio recording, your agent's
                        full configuration (system prompt, greeting, capabilities, configured client actions), the structured
                        transcript (with the agent's tool calls), the client action events log, and the raw session report are
                        all sent to a multimodal LLM for a qualitative QA score and concrete prompt-improvement suggestions.

                        API keys, MCP server URLs, and other secrets in your agent's configuration are not
                        sent to the evaluator. Limited to 100 evals/day per user; recordings must be ≤18 MB.

                        # Basic eval against the agent's own configuration
vb eval <session_id>

# With an explicit objective (what the agent should accomplish)
vb eval <session_id> --objective "Schedule an interview for next Tuesday"

# With both an objective and an expected scenario
vb eval <session_id> \
  --objective "Confirm the candidate's availability" \
  --scenario "User is busy and tries to reschedule twice"

# Long objective/scenario from files
vb eval <session_id> --objective-file objective.txt --scenario-file scenario.txt

# Raw JSON output (pipe-friendly)
vb eval <session_id> --json

                    Example Workflow

                        # 1. Check current agent setup
vb agent
vb prompt show

# 2. Make some test calls to your agent...

# 3. Review call logs
vb logs
vb logs show <session_id>

# 4. Download a recording for analysis
vb logs download <session_id>

# 5. Run an automated eval against an objective (Pilot only)
vb eval <session_id> --objective "Confirm the user's availability"

# 6. Update the prompt based on findings
vb prompt edit

# 7. Check statistics
vb stats

                    Environment Variables

                    You can also set credentials via environment variables:

                        export VOCAL_BRIDGE_API_KEY=vb_your_api_key_here
export VOCAL_BRIDGE_API_URL=https://vocalbridgeai.com  # optional

                    Troubleshooting

                            "No API key found"

                            Run vb auth login or set the VOCAL_BRIDGE_API_KEY environment variable.

                            "Invalid API key"

                            Check that your key starts with vb_ and hasn't been revoked. Generate a new key if needed.

                            "Agent not found"

                            The API key may have been created for a deleted agent. Create a new key from an active agent.

                    Links

                        CLI on PyPI

                Claude Code Plugin

                        The Vocal Bridge plugin for Claude Code
                        lets you manage your voice agents directly from the command line. View call logs, update prompts,
                        stream debug events, and iterate on your agent without leaving your terminal.

                                Works with Claude Code

                                    Install the plugin in Claude Code to get native slash commands for managing your voice agent.
                                    Claude can automatically use these commands when you ask about your agent.

                    Installation

                    Install the plugin from the Vocal Bridge marketplace:

                        /plugin marketplace add vocalbridgeai/vocal-bridge-marketplace
/plugin install vocal-bridge@vocal-bridge

                    Getting Started

                    After installing, authenticate with your API key:

                        /vocal-bridge:login vb_your_api_key_here

                        Get an agent API key from your agent's detail page,
                        or create an account API key from the dashboard's "API Keys" tab.

                    Available Commands

                                    Command
                                    Description

                                    /vocal-bridge:login
                                    Authenticate with your API key

                                    /vocal-bridge:status
                                    Check authentication status

                                    /vocal-bridge:agent
                                    Show agent information (name, mode, phone number)

                                    /vocal-bridge:create
                                    Create and deploy a new agent (Pilot subscribers only)

                                    /vocal-bridge:logs
                                    View call logs and transcripts

                                    /vocal-bridge:download
                                    Download call recording for a session

                                    /vocal-bridge:stats
                                    Show call statistics

                                    /vocal-bridge:prompt
                                    View or update system prompt

                                    /vocal-bridge:config
                                    View and update all agent configuration settings

                                    /vocal-bridge:eval <session_id>
                                    Evaluate a call recording with a multimodal LLM (Pilot only, 100/day)

                                    /vocal-bridge:debug
                                    Stream real-time debug events

                                    /vocal-bridge:help
                                    Show all available commands

                    Example Workflow

                        # Check recent calls
/vocal-bridge:logs

# View a specific call transcript
/vocal-bridge:logs 550e8400-e29b-41d4-a716-446655440000

# Download a call recording
/vocal-bridge:download 550e8400-e29b-41d4-a716-446655440000

# Find failed calls
/vocal-bridge:logs --status failed

# Check statistics
/vocal-bridge:stats

# View current prompt
/vocal-bridge:prompt show

# View and update agent configuration
/vocal-bridge:config

# Stream debug events while testing
/vocal-bridge:debug

                    Benefits

                                Stay in Flow

                            No context switching between terminal and browser

                                AI-Assisted

                            Claude can use commands automatically when you ask about your agent

                                Real-time Debug

                            Stream live events while making test calls

                                Quick Iteration

                            Update prompts and test changes rapidly

                    Links

                        Plugin Repository - Source code and documentation

                        Marketplace Repository - Plugin registry

                        CLI on PyPI - Standalone CLI (also usable outside Claude Code)

                Advanced: Direct WebRTC Integration

                        If you need lower-level control, you can use the LiveKit SDK directly instead of the Vocal Bridge SDK.
                        This is useful for platforms where the JS SDK isn't available or when you need full control over the WebRTC layer.

                            For most use cases, the JavaScript SDK or
                            React SDK above is recommended.
                            The direct approach requires significantly more code.

                    JavaScript (Direct)

                        import { Room, RoomEvent, Track } from 'livekit-client';

const room = new Room();

// Handle agent audio
room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
  if (track.kind === Track.Kind.Audio) {
    const audioElement = track.attach();
    document.body.appendChild(audioElement);
  }
});

// Get token from your backend
const response = await fetch('/api/voice-token');
const { url, token } = await response.json();

// Connect and enable mic
await room.connect(url, token);
await room.localParticipant.setMicrophoneEnabled(true);

// Handle data channel messages (transcript, actions, etc.)
room.on(RoomEvent.DataReceived, (payload, participant, kind, topic) => {
  if (topic === 'client_actions') {
    const data = JSON.parse(new TextDecoder().decode(payload));
    if (data.type === 'client_action') {
      console.log('Action:', data.action, data.payload);
    }
  }
});

// Send actions
room.localParticipant.publishData(
  new TextEncoder().encode(JSON.stringify({
    type: 'client_action',
    action: 'user_clicked_buy',
    payload: { productId: '123' }
  })),
  { reliable: true, topic: 'client_actions' }
);

// Disconnect
await room.disconnect();

                    Data Channel Protocol

                    All messages use topic client_actions with this envelope format:

                        {
  "type": "client_action",
  "action": "action_name",
  "payload": { ... }
}

                    Built-in actions handled by the platform:

                        heartbeat / heartbeat_ack — Agent keepalive

                        send_transcript — Transcript entry { role, text, timestamp }

                        query_agent / agent_response — AI Agent query/response flow

                        stop_talking / start_talking — Mute / un-mute the agent on demand (app→agent). stop_talking mutes the agent until start_talking; { mode } (default "reply") controls the reply in progress: "reply" lets it finish, "immediate" cuts it off right away. start_talking optionally takes { text } (treated as the user's message) and/or { instructions } (steers the resumed reply without adding a user turn); if both are specified, instructions takes priority. To resume an interrupted thought, send { instructions: "continue where you left off" } — the agent regenerates the continuation from context (the dropped tail isn't needed). The agent reports state back via talking_state_changed { state: "stopped" | "started" }.

                    Dependencies

                        # JavaScript
npm install livekit-client

# Python
pip install livekit requests

# Flutter (pubspec.yaml)
dependencies:
  livekit_client: ^2.3.0
  http: ^1.2.0

                        Need more help? Contact [email protected]
