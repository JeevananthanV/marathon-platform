import React from 'react';
import { RaceCategory } from '@/types';

interface RaceCategoriesSectionProps {
  categories: RaceCategory[];
  onSelectCategory: (category: RaceCategory) => void;
}

export const RaceCategoriesSection: React.FC<RaceCategoriesSectionProps> = ({
  categories,
  onSelectCategory,
}) => {
  // Category perks mapping
  const categoryHighlights: Record<string, string[]> = {
    '21K': [
      'Official RFID Timing Chip Bib',
      'Heavy-Cast Finisher Medal',
      'Premium Dri-FIT Running Tee',
      'Hot Post-Race Breakfast',
      'Digital Timing Certificate',
      'Pacer Groups (1:45 to 2:45)',
    ],
    '10K': [
      'Official RFID Timing Chip Bib',
      'Heavy-Cast Finisher Medal',
      'Dri-FIT Event T-Shirt',
      'Hot Post-Race Breakfast',
      'Digital Timing Certificate',
      'Medical & Physio Support',
    ],
    '5K': [
      'Finisher Commemorative Medal',
      'Event Souvenir T-Shirt',
      'Hot Post-Race Breakfast',
      'E-Certificate of Participation',
      'Hydration & Energy Snacks',
      'Fun Family & Beginner Friendly',
    ],
  };

  return (
    <section id="categories" className="py-16 sm:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12 transition-colors">
      
      {/* Section Heading */}
      <div className="text-center space-y-3 max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-semibold uppercase tracking-wider border border-amber-200">
          Official Categories
        </div>
        <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
          Select Your Challenge
        </h2>
        <p className="text-slate-600 text-sm">
          Whether you're aiming for a personal record or enjoying a morning run with family, we have a route for you.
        </p>
      </div>

      {/* Category Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
        {categories.map((cat) => {
          const isFeatured = cat.code === '21K';
          const isSoldOut = cat.slots_remaining <= 0;
          const perks = categoryHighlights[cat.code] || [
            'Finisher Medal',
            'Event T-Shirt',
            'Post-Race Breakfast',
            'E-Certificate',
          ];

          return (
            <div
              key={cat.id}
              className={`relative rounded-3xl p-6 sm:p-8 flex flex-col justify-between transition-all duration-300 ${
                isFeatured
                  ? 'bg-white border-2 border-amber-500 shadow-xl shadow-amber-500/10 sm:-translate-y-2'
                  : 'bg-white border border-slate-200 hover:border-slate-300 hover:shadow-lg shadow-sm'
              }`}
            >
              {/* Featured Badge */}
              {isFeatured && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 bg-amber-500 text-slate-950 text-xs font-black uppercase tracking-wider rounded-full shadow-md">
                  Most Popular • Timed
                </div>
              )}

              <div className="space-y-6">
                
                {/* Header Info */}
                <div className="flex items-center justify-between">
                  <span className="px-3 py-1 rounded-lg text-xs font-mono font-bold bg-slate-100 text-slate-800 border border-slate-200">
                    {cat.code}
                  </span>
                  <span className="text-xs text-slate-500 font-medium">
                    Flag-off: <strong className="text-slate-800 font-bold">{cat.start_time}</strong>
                  </span>
                </div>

                {/* Title & Distance */}
                <div>
                  <h3 className="text-2xl font-black text-slate-900">{cat.title}</h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Distance: <strong className="text-slate-700 font-semibold">{cat.distance_km} KM</strong> • Min Age: {cat.min_age} Yrs
                  </p>
                </div>

                {/* Price */}
                <div className="pt-2 pb-4 border-y border-slate-100 flex items-baseline gap-2">
                  <span className="text-3xl sm:text-4xl font-extrabold text-slate-900">
                    ₹{cat.price_inr}
                  </span>
                  <span className="text-xs text-slate-500 font-normal">/ entry pass</span>
                </div>

                {/* Slots Availability Meter */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">Available Slots:</span>
                    <span className="font-mono text-amber-600 font-bold">
                      {isSoldOut ? 'Sold Out' : `${cat.slots_remaining} of ${cat.max_capacity}`}
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden border border-slate-200">
                    <div
                      className={`h-full transition-all duration-500 ${
                        isSoldOut
                          ? 'bg-rose-500'
                          : 'bg-gradient-to-r from-amber-500 to-amber-400'
                      }`}
                      style={{
                        width: `${Math.min(100, (cat.current_count / cat.max_capacity) * 100)}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Perks Checklist */}
                <div className="space-y-2.5 pt-2">
                  <div className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                    Included in Race Kit:
                  </div>
                  <ul className="space-y-2 text-xs text-slate-600">
                    {perks.map((perk, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <span className="text-emerald-600 font-bold">✓</span>
                        <span>{perk}</span>
                      </li>
                    ))}
                  </ul>
                </div>

              </div>

              {/* Action Button */}
              <div className="mt-8 pt-4">
                <button
                  onClick={() => onSelectCategory(cat)}
                  disabled={isSoldOut}
                  className={`w-full py-3.5 px-6 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 ${
                    isSoldOut
                      ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                      : isFeatured
                      ? 'bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-slate-950 shadow-md shadow-amber-500/20 active:scale-95'
                      : 'bg-slate-100 hover:bg-amber-500 text-slate-800 hover:text-slate-950 border border-slate-200 active:scale-95'
                  }`}
                >
                  {isSoldOut ? 'Sold Out' : `Register for ${cat.code} →`}
                </button>
              </div>

            </div>
          );
        })}
      </div>

    </section>
  );
};
