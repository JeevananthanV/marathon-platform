import React from 'react';

interface FooterProps {
  onAdminClick?: () => void;
}

export const Footer: React.FC<FooterProps> = ({ onAdminClick }) => {
  return (
    <footer className="bg-white border-t border-slate-200 pt-16 pb-24 md:pb-16 text-slate-600 text-xs transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          
          {/* Brand Col */}
          <div className="space-y-4 md:col-span-2">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center text-slate-950 font-black text-base shadow-sm">
                🏃
              </div>
              <span className="font-black text-base text-slate-900">CITY MARATHON 2026</span>
            </div>
            <p className="text-slate-600 max-w-sm leading-relaxed">
              Bengaluru’s premier running celebration promoting health, endurance, and community spirit. Certified flat route, electronic chip timing, and world-class hydration support.
            </p>
            <div className="text-[11px] text-slate-500 font-mono">
              Venue: Kanteerava Outdoor Stadium, Bengaluru, Karnataka 560001
            </div>
          </div>

          {/* Quick Links */}
          <div className="space-y-3">
            <h4 className="font-bold text-slate-900 uppercase text-[11px] tracking-wider">Event Links</h4>
            <ul className="space-y-2">
              <li><a href="#categories" className="hover:text-amber-600 transition-colors">Race Categories (5K/10K/21K)</a></li>
              <li><a href="#perks" className="hover:text-amber-600 transition-colors">Finisher Kits & Medals</a></li>
              <li><a href="#schedule" className="hover:text-amber-600 transition-colors">Race Day Schedule</a></li>
              <li><a href="#faqs" className="hover:text-amber-600 transition-colors">Runner FAQ & Guidelines</a></li>
              {onAdminClick && (
                <li>
                  <button
                    onClick={onAdminClick}
                    className="text-amber-700 hover:text-amber-800 font-bold transition-colors uppercase tracking-wider text-[11px]"
                  >
                    Organizer Admin Portal →
                  </button>
                </li>
              )}
            </ul>
          </div>

          {/* Helpline & Support */}
          <div className="space-y-3">
            <h4 className="font-bold text-slate-900 uppercase text-[11px] tracking-wider">Helpline & Support</h4>
            <div className="space-y-1.5 text-slate-600">
              <p>Email: <strong className="text-slate-900 font-semibold">support@citymarathon2026.com</strong></p>
              <p>WhatsApp Helpdesk: <strong className="text-slate-900 font-semibold">+91 98765 43210</strong></p>
              <p>Hours: Mon - Sat (09:00 AM - 07:00 PM)</p>
            </div>
          </div>

        </div>

        {/* Bottom copyright */}
        <div className="pt-8 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-slate-500">
          <p>© 2026 City Marathon Organizing Committee. All rights reserved.</p>
          <div className="flex gap-4">
            <a href="#faqs" className="hover:text-slate-700">Terms & Conditions</a>
            <a href="#faqs" className="hover:text-slate-700">Privacy Policy</a>
            <a href="#faqs" className="hover:text-slate-700">Refund Guidelines</a>
          </div>
        </div>

      </div>
    </footer>
  );
};
