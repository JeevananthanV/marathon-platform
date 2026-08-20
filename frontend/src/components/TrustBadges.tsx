import React from 'react';

export const TrustBadges: React.FC = () => {
  const features = [
    {
      icon: '📐',
      title: 'AIMS Certified Course',
      desc: 'Officially measured flat-elevation route, perfect for personal bests and qualifier timings.',
    },
    {
      icon: '⏱️',
      title: 'RFID Chip Timing',
      desc: 'Accurate electronic bib-tag timing with instant split alerts and digital completion certificate.',
    },
    {
      icon: '🚑',
      title: 'Paramedic & Physio Stations',
      desc: 'Medical ambulances stationed every 2 KM with emergency response and post-run muscle recovery.',
    },
    {
      icon: '💧',
      title: 'Hydration & Energy Gels',
      desc: 'Well-stocked water, isotonic electrolytes, oranges, and fast carb gels along the course.',
    },
  ];

  return (
    <section className="py-10 border-y border-slate-200 bg-white transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((item, idx) => (
            <div
              key={idx}
              className="p-5 rounded-2xl bg-slate-50 border border-slate-200 hover:border-amber-300 hover:shadow-md transition-all space-y-2.5"
            >
              <div className="text-3xl">{item.icon}</div>
              <h3 className="font-bold text-slate-900 text-base">{item.title}</h3>
              <p className="text-xs text-slate-600 leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
