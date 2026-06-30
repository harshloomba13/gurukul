import { Suspense } from 'react';
import { QuarterObserver } from '../../components/QuarterObserver';

export default function ObserverPage() {
  return (
    <main className="app-shell observer-page">
      <Suspense fallback={<div className="observer-loading">Loading observer</div>}>
        <QuarterObserver />
      </Suspense>
    </main>
  );
}
