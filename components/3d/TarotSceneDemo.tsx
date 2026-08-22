'use client';

import { useState } from 'react';
import TarotScene from './TarotScene';

export default function TarotSceneDemo() {
  const [isSynchronized, setIsSynchronized] = useState(false);

  return (
    <section className="bg-[#090b0f] px-4 pb-10 sm:px-8 lg:px-12">
      <div className="mx-auto max-w-7xl">
        <div className="mb-3 flex items-center justify-between gap-4">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-stone-500">Spatial observatory</p>
            <h2 className="mt-1 text-xl font-medium text-stone-100">THE DATA TORNADO</h2>
          </div>
          <button
            type="button"
            onClick={() => setIsSynchronized((current) => !current)}
            className={`border px-4 py-2 font-mono text-[10px] uppercase tracking-[0.2em] transition-colors ${isSynchronized ? 'border-amber-200/70 bg-amber-200 text-slate-950' : 'border-white/20 bg-white/5 text-stone-300 hover:border-white/50'}`}
          >
            {isSynchronized ? 'Release deep dive' : 'Trigger Emperor sync'}
          </button>
        </div>
        <TarotScene
          data={{
            cardName: 'THE EMPEROR',
            symbol: 'US500',
            wuxingPhase: 'FIRE',
            isEmperorSynchronized: isSynchronized,
            s15Volume: isSynchronized ? 900 : 280,
            s15Delta: isSynchronized ? -70 : -12,
          }}
        />
      </div>
    </section>
  );
}
