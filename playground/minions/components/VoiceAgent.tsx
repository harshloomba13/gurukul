'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { AlertCircle, Loader2, Mic, MicOff, Phone, PhoneOff, Trash2 } from 'lucide-react';
import { ConnectionState } from '@vocalbridgeai/sdk';
import {
  VocalBridgeProvider,
  useTranscript,
  useVocalBridge,
} from '@vocalbridgeai/react';

function VoiceAgentConsole() {
  const {
    state,
    connect,
    disconnect,
    isMicrophoneEnabled,
    toggleMicrophone,
    error,
  } = useVocalBridge();
  const { transcript, clear } = useTranscript();
  const [isBusy, setIsBusy] = useState(false);
  const searchParams = useSearchParams();
  const autoStartAttempted = useRef(false);

  const normalizedState = String(state || ConnectionState.Disconnected);
  const isDisconnected = state === ConnectionState.Disconnected || normalizedState === 'disconnected';
  const isConnecting = normalizedState === 'connecting' || normalizedState === 'waiting_for_agent';
  const stateLabel = normalizedState.replace(/_/g, ' ');
  const autoStart = searchParams.get('autostart') === '1';

  async function runVoiceAction(action: () => Promise<void>) {
    setIsBusy(true);
    try {
      await action();
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(() => {
    if (!autoStart || autoStartAttempted.current) {
      return;
    }

    if (!isDisconnected || isConnecting || isBusy) {
      return;
    }

    autoStartAttempted.current = true;
    void runVoiceAction(connect);
  }, [autoStart, isBusy, connect, isConnecting, isDisconnected]);

  return (
    <section className="voice-console" aria-label="Voice agent">
      <header className="voice-header">
        <div>
          <p className="eyebrow">Gurukul agent</p>
          <h1>Voice session</h1>
        </div>
        <div className="status-pill" data-state={normalizedState}>
          <span aria-hidden="true" />
          {stateLabel}
        </div>
      </header>

      {error ? (
        <div className="alert" role="alert">
          <AlertCircle size={18} aria-hidden="true" />
          <span>{error.message}</span>
        </div>
      ) : null}

      <div className="controls" aria-label="Call controls">
        {isDisconnected ? (
          <button
            className="primary-button"
            type="button"
            onClick={() => runVoiceAction(connect)}
            disabled={isBusy}
            title="Start voice chat"
          >
            {isBusy ? <Loader2 className="spin" size={18} /> : <Phone size={18} />}
            <span>Start</span>
          </button>
        ) : (
          <button
            className="danger-button"
            type="button"
            onClick={() => runVoiceAction(disconnect)}
            disabled={isBusy}
            title="End call"
          >
            {isBusy ? <Loader2 className="spin" size={18} /> : <PhoneOff size={18} />}
            <span>End</span>
          </button>
        )}

        <button
          className="icon-button"
          type="button"
          onClick={() => runVoiceAction(toggleMicrophone)}
          disabled={isDisconnected || isConnecting || isBusy}
          title={isMicrophoneEnabled ? 'Mute microphone' : 'Unmute microphone'}
          aria-label={isMicrophoneEnabled ? 'Mute microphone' : 'Unmute microphone'}
        >
          {isMicrophoneEnabled ? <Mic size={18} /> : <MicOff size={18} />}
        </button>

        <button
          className="icon-button"
          type="button"
          onClick={clear}
          disabled={transcript.length === 0}
          title="Clear transcript"
          aria-label="Clear transcript"
        >
          <Trash2 size={18} />
        </button>
      </div>

      <div className="transcript" aria-live="polite">
        {transcript.length === 0 ? (
          <p className="empty-state">Transcript</p>
        ) : (
          transcript.map((entry, index) => (
            <article className="transcript-entry" data-role={entry.role} key={`${entry.timestamp}-${index}`}>
              <span>{entry.role === 'user' ? 'You' : 'Agent'}</span>
              <p>{entry.text}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

export function VoiceAgent() {
  const options = useMemo(
    () => ({
      auth: { tokenUrl: '/api/voice-token' },
      participantName: 'Web User',
      debug: process.env.NODE_ENV === 'development',
    }),
    [],
  );

  return (
    <VocalBridgeProvider options={options}>
      <VoiceAgentConsole />
    </VocalBridgeProvider>
  );
}
