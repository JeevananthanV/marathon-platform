import React from 'react';

interface NavbarProps {
  onRegisterClick: () => void;
  onPassLookupClick: () => void;
  onAdminClick?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onRegisterClick,
  onPassLookupClick,
  onAdminClick,
}) => {
  return (
    <header className="sticky top-0 z-40 w-full backdrop-blur-md bg-white/95 border-b border-slate-200 shadow-sm transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 sm:h-20 flex items-center justify-between">
        
        {/* Brand Logo */}
        <a href="#" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-amber-400 flex items-center justify-center text-slate-950 font-black text-xl shadow-md shadow-amber-500/20 group-hover:scale-105 transition-transform">
            🏃
          </div>
          <div>
            <div className="font-extrabold text-base sm:text-lg tracking-tight text-slate-900 flex items-center gap-1.5">
              CITY MARATHON <span className="text-amber-500 font-black">2026</span>
            </div>
            <div className="text-[10px] text-slate-500 font-semibold tracking-wider uppercase">
              Bengaluru • Oct 18, 2026
            </div>
          </div>
        </a>

        {/* Desktop Nav Links */}
        <nav className="hidden md:flex items-center gap-6 text-xs font-semibold text-slate-600">
          <a href="#categories" className="hover:text-amber-600 transition-colors">
            Race Categories
          </a>
          <a href="#perks" className="hover:text-amber-600 transition-colors">
            Finisher Perks
          </a>
          <a href="#schedule" className="hover:text-amber-600 transition-colors">
            Schedule & Route
          </a>
          <a href="#faqs" className="hover:text-amber-600 transition-colors">
            FAQs
          </a>
          <button
            onClick={onPassLookupClick}
            className="text-slate-600 hover:text-slate-900 transition-colors font-semibold"
          >
            Find My Ticket
          </button>
          {onAdminClick && (
            <button
              onClick={onAdminClick}
              className="text-amber-700 hover:text-amber-800 font-bold transition-colors uppercase tracking-wider text-[11px] border border-amber-300 px-2.5 py-1 rounded-lg bg-amber-50 hover:bg-amber-100"
            >
              Admin Portal
            </button>
          )}
        </nav>

        {/* CTA Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={onPassLookupClick}
            className="hidden sm:inline-flex md:hidden text-xs font-semibold text-slate-600 hover:text-slate-900 px-3 py-2"
          >
            My Ticket
          </button>
          
          <button
            onClick={onRegisterClick}
            className="py-2.5 px-5 sm:px-6 bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-slate-950 font-extrabold text-xs sm:text-sm rounded-xl shadow-md shadow-amber-500/20 active:scale-95 transition-all flex items-center gap-1.5"
          >
            <span>Register Now</span>
            <span className="hidden sm:inline">⚡</span>
          </button>
        </div>

      </div>
    </header>
  );
};
