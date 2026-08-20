import React from 'react';

export const FinisherPerksSection: React.FC = () => {
  const perks = [
    {
      emoji: '👕',
      title: 'Dri-FIT Running Tee',
      desc: 'Breathable, ultra-lightweight running jersey engineered for maximum sweat-wicking comfort.',
      tag: 'All Runners',
    },
    {
      emoji: '🏅',
      title: 'Heavy-Cast Metal Medal',
      desc: 'Custom-molded 3D embossed marathon medal honoring your grit and finish-line triumph.',
      tag: 'Finishers',
    },
    {
      emoji: '⚡',
      title: 'RFID Timing Chip Bib',
      desc: 'High-precision micro-transponder bib measuring exact chip time, gun time, and sector splits.',
      tag: 'Timed (10K / 21K)',
    },
    {
      emoji: '🍳',
      title: 'Hot Energy Breakfast',
      desc: 'Nutritious post-run breakfast spread with bananas, electrolytes, juices, and hot meals.',
      tag: 'All Runners',
    },
    {
      emoji: '📜',
      title: 'E-Certificate & Splits',
      desc: 'Downloadable digital verified timing certificate with overall category ranking.',
      tag: 'All Runners',
    },
    {
      emoji: '📸',
      title: 'Free HD Action Photos',
      desc: 'Professional course-side photographers snapping your iconic finish line moments by bib lookup.',
      tag: 'Free Download',
    },
  ];

  return (
    <section id="perks" className="py-16 sm:py-24 bg-slate-100/70 border-t border-slate-200 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        
        {/* Section Heading */}
        <div className="text-center space-y-3 max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-semibold uppercase tracking-wider border border-amber-200">
            Runner Experience
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            What's Inside Your Race Kit
          </h2>
          <p className="text-slate-600 text-sm">
            Every registered participant receives premium runner gear and full race-day hospitality.
          </p>
        </div>

        {/* Perks Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {perks.map((p, idx) => (
            <div
              key={idx}
              className="p-6 rounded-2xl bg-white border border-slate-200 hover:border-slate-300 hover:shadow-md shadow-sm transition-all flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-4xl">{p.emoji}</span>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-50 text-amber-800 border border-amber-200">
                    {p.tag}
                  </span>
                </div>
                <h3 className="font-bold text-slate-900 text-lg">{p.title}</h3>
                <p className="text-xs text-slate-600 leading-relaxed">{p.desc}</p>
              </div>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
};
