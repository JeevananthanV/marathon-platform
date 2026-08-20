import React, { useState, useEffect } from 'react';

interface HeroSectionProps {
  onRegisterClick: (categoryCode?: string) => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onRegisterClick }) => {
  // Target Event Date: October 18, 2026 05:30 AM
  const [timeLeft, setTimeLeft] = useState({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0,
  });

  useEffect(() => {
    // 60 days countdown fallback or calculated from target date
    const target = new Date('2026-10-18T05:30:00+05:30').getTime();

    const interval = setInterval(() => {
      const now = new Date().getTime();
      const difference = target - now;

      if (difference > 0) {
        setTimeLeft({
          days: Math.floor(difference / (1000 * 60 * 60 * 24)),
          hours: Math.floor((difference / (1000 * 60 * 60)) % 24),
          minutes: Math.floor((difference / 1000 / 60) % 60),
          seconds: Math.floor((difference / 1000) % 60),
        });
      } else {
        setTimeLeft({ days: 45, hours: 14, minutes: 22, seconds: 10 });
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <section className="relative overflow-hidden bg-slate-50 pt-10 pb-16 sm:pt-16 sm:pb-24 transition-colors">
      {/* Subtle Ambient Background Light */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] sm:w-[750px] h-[350px] bg-amber-500/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute top-1/3 left-1/4 w-[300px] h-[300px] bg-emerald-500/5 blur-[100px] rounded-full pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col items-center text-center space-y-8">
        
        {/* Top Urgency / Attribution Pill */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white border border-amber-300 shadow-sm text-xs font-semibold text-amber-800">
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
          </span>
          <span>🔥 Early-Bird Phase 1 Registrations Open • Flat 20% Off Applied</span>
        </div>

        {/* Primary Headline */}
        <div className="max-w-4xl space-y-4">
          <h1 className="text-3xl sm:text-5xl md:text-6xl lg:text-7xl font-black tracking-tight text-slate-900 uppercase leading-none">
            Unleash Your Pace. <br />
            <span className="text-amber-500">
              Conquer City Marathon 2026.
            </span>
          </h1>
          <p className="text-slate-600 text-sm sm:text-lg max-w-2xl mx-auto font-normal leading-relaxed">
            Join over 5,000+ runners across Bengaluru's scenic, certified expressway routes. 
            Timed 21K Half Marathon, 10K Challenge, and 5K Fun Run.
          </p>
        </div>

        {/* Event Chips */}
        <div className="flex flex-wrap items-center justify-center gap-2.5 sm:gap-4 text-xs font-medium text-slate-700">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-white border border-slate-200 shadow-sm">
            <span>📅</span>
            <span>Sunday, October 18, 2026</span>
          </div>
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-white border border-slate-200 shadow-sm">
            <span>📍</span>
            <span>Kanteerava Stadium, Bengaluru</span>
          </div>
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-white border border-slate-200 shadow-sm">
            <span>🏅</span>
            <span>AIMS Certified Course</span>
          </div>
        </div>

        {/* Live Countdown Timer Card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-6 shadow-md">
          <div className="text-[11px] uppercase tracking-widest text-slate-500 font-bold mb-3">
            Flag-off Countdown
          </div>
          <div className="grid grid-cols-4 gap-2 sm:gap-4 text-center font-mono">
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5 sm:p-4 min-w-[65px] sm:min-w-[85px]">
              <div className="text-xl sm:text-3xl font-black text-amber-500">{timeLeft.days}</div>
              <div className="text-[10px] sm:text-xs text-slate-500 uppercase font-sans font-semibold">Days</div>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5 sm:p-4 min-w-[65px] sm:min-w-[85px]">
              <div className="text-xl sm:text-3xl font-black text-slate-900">{timeLeft.hours}</div>
              <div className="text-[10px] sm:text-xs text-slate-500 uppercase font-sans font-semibold">Hours</div>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5 sm:p-4 min-w-[65px] sm:min-w-[85px]">
              <div className="text-xl sm:text-3xl font-black text-slate-900">{timeLeft.minutes}</div>
              <div className="text-[10px] sm:text-xs text-slate-500 uppercase font-sans font-semibold">Mins</div>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5 sm:p-4 min-w-[65px] sm:min-w-[85px]">
              <div className="text-xl sm:text-3xl font-black text-amber-500">{timeLeft.seconds}</div>
              <div className="text-[10px] sm:text-xs text-slate-500 uppercase font-sans font-semibold">Secs</div>
            </div>
          </div>
        </div>

        {/* Primary & Secondary CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-4 w-full max-w-md">
          <button
            onClick={() => onRegisterClick()}
            className="w-full sm:flex-1 py-4 px-8 bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-slate-950 font-black text-base rounded-2xl shadow-lg shadow-amber-500/25 active:scale-95 transition-all flex items-center justify-center gap-2 group"
          >
            <span>Register in 2 Minutes</span>
            <span className="group-hover:translate-x-1 transition-transform">→</span>
          </button>
          
          <a
            href="#categories"
            className="w-full sm:flex-1 py-4 px-6 bg-white hover:bg-slate-50 border border-slate-300 text-slate-800 font-bold text-sm rounded-2xl shadow-sm transition-all flex items-center justify-center"
          >
            View Race Tiers (₹499+)
          </a>
        </div>

        {/* Social Proof Strip */}
        <div className="flex items-center gap-3 pt-2 text-xs text-slate-500">
          <div className="flex -space-x-2 overflow-hidden">
            <div className="inline-block h-7 w-7 rounded-full ring-2 ring-white bg-slate-200 flex items-center justify-center text-xs">🏃‍♂️</div>
            <div className="inline-block h-7 w-7 rounded-full ring-2 ring-white bg-amber-200 flex items-center justify-center text-xs">🏃‍♀️</div>
            <div className="inline-block h-7 w-7 rounded-full ring-2 ring-white bg-emerald-200 flex items-center justify-center text-xs">🏃</div>
          </div>
          <p>
            <strong className="text-slate-900 font-bold">1,480+ Runners</strong> already confirmed. Limited slots per category.
          </p>
        </div>

      </div>
    </section>
  );
};
