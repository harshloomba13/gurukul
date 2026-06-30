import { Suspense } from 'react';
import { VoiceAgent } from '../components/VoiceAgent';

export default function Home() {
  return (
    <main className="app-shell">
      <Suspense fallback={<div className="observer-loading">Loading voice session</div>}>
        <VoiceAgent />
      </Suspense>
    </main>
  );
}
