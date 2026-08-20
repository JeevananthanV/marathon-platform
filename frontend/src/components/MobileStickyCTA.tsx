import React from 'react';

interface MobileStickyCTAProps {
  onRegisterClick: () => void;
}

export const MobileStickyCTA: React.FC<MobileStickyCTAProps> = ({ onRegisterClick }) => {
  return (
    <div className="fixed bottom-0 inset-x-0 z-40 md:hidden bg-white/95 backdrop-blur-lg border-t border-slate-200 p-3.5 shadow-xl transition-colors">
      <div className="flex items-center justify-between gap-3 max-w-md mx-auto">
        <div className="space-y-0.5">
          <div className="text-[11px] font-black text-amber-600 uppercase tracking-wide">
            🔥 Early-Bird Open
          </div>
          <div className="text-xs text-slate-900 font-bold">
            5K, 10K & 21K • From ₹499
          </div>
        </div>

        <button
          onClick={onRegisterClick}
          className="py-2.5 px-6 bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-slate-950 font-black text-xs rounded-xl shadow-md shadow-amber-500/25 active:scale-95 transition-all flex items-center gap-1.5 whitespace-nowrap"
        >
          <span>Register Now</span>
          <span>⚡</span>
        </button>
      </div>
    </div>
  );
};
