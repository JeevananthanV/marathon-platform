import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { useUTM } from '@/hooks/useUTM';
import { RaceCategory } from '@/types';

import { Navbar } from '@/components/Navbar';
import { HeroSection } from '@/components/HeroSection';
import { TrustBadges } from '@/components/TrustBadges';
import { RaceCategoriesSection } from '@/components/RaceCategoriesSection';
import { FinisherPerksSection } from '@/components/FinisherPerksSection';
import { RouteAndScheduleSection } from '@/components/RouteAndScheduleSection';
import { FaqSection } from '@/components/FaqSection';
import { RegistrationModal } from '@/components/RegistrationModal';
import { SuccessPassModal } from '@/components/SuccessPassModal';
import { MobileStickyCTA } from '@/components/MobileStickyCTA';
import { Footer } from '@/components/Footer';
import { AdminPortal } from '@/components/admin/AdminPortal';

export default function App() {
  // Capture & persist UTM attribution for Meta / IG / FB ads
  useUTM();

  const [isAdminView, setIsAdminView] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const path = window.location.pathname.toLowerCase();
      const params = new URLSearchParams(window.location.search);
      const hash = window.location.hash.toLowerCase();
      return path === '/admin' || path.startsWith('/admin/') || params.get('view') === 'admin' || params.get('admin') === 'true' || hash === '#admin';
    }
    return false;
  });

  const [categories, setCategories] = useState<RaceCategory[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedCategory, setSelectedCategory] = useState<RaceCategory | null>(null);
  const [isRegisterModalOpen, setIsRegisterModalOpen] = useState<boolean>(false);
  const [activeSuccessCode, setActiveSuccessCode] = useState<string | null>(null);

  // Ticket lookup prompt state
  const [isLookupOpen, setIsLookupOpen] = useState<boolean>(false);
  const [lookupCodeInput, setLookupCodeInput] = useState<string>('');

  // Fetch race categories and check URL params on mount
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const data = await api.getCategories();
        setCategories(data);

        // Check if URL has ?reg=MX26-000001
        const params = new URLSearchParams(window.location.search);
        const regParam = params.get('reg') || params.get('registration_code') || params.get('ticket');
        if (regParam) {
          setActiveSuccessCode(regParam);
        }

        // Check if URL has ?cat=21K to open modal directly
        const catParam = params.get('cat') || params.get('category');
        if (catParam) {
          const match = data.find(
            (c) => c.code.toLowerCase() === catParam.toLowerCase() || c.id === catParam
          );
          if (match) {
            setSelectedCategory(match);
            setIsRegisterModalOpen(true);
          }
        }
      } catch (err) {
        console.error('Failed to load categories', err);
        // Fallback offline mock data for resilience
        const fallbackCats: RaceCategory[] = [
          {
            id: '5k-mock-id',
            title: '5K Fun Run',
            code: '5K',
            distance_km: 5.0,
            price_inr: 499.0,
            max_capacity: 500,
            current_count: 85,
            slots_remaining: 415,
            bib_prefix: '5K',
            min_age: 8,
            start_time: '06:30 AM',
            is_active: true,
          },
          {
            id: '10k-mock-id',
            title: '10K Timed Run',
            code: '10K',
            distance_km: 10.0,
            price_inr: 899.0,
            max_capacity: 500,
            current_count: 140,
            slots_remaining: 360,
            bib_prefix: '10K',
            min_age: 12,
            start_time: '06:00 AM',
            is_active: true,
          },
          {
            id: '21k-mock-id',
            title: '21K Half Marathon',
            code: '21K',
            distance_km: 21.1,
            price_inr: 1499.0,
            max_capacity: 300,
            current_count: 220,
            slots_remaining: 80,
            bib_prefix: 'HM',
            min_age: 18,
            start_time: '05:30 AM',
            is_active: true,
          },
        ];
        setCategories(fallbackCats);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const handleOpenRegister = (category?: RaceCategory) => {
    if (category) {
      setSelectedCategory(category);
    } else if (categories.length > 0) {
      setSelectedCategory(categories[0]);
    }
    setIsRegisterModalOpen(true);
  };

  const handleRegistrationSuccess = (regCode: string) => {
    setIsRegisterModalOpen(false);
    setActiveSuccessCode(regCode);
  };

  const handleLookupSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (lookupCodeInput.trim()) {
      setIsLookupOpen(false);
      setActiveSuccessCode(lookupCodeInput.trim().toUpperCase());
    }
  };

  const handleSwitchToAdmin = () => {
    setIsAdminView(true);
    if (window.history.pushState) {
      window.history.pushState(null, '', '/admin');
    }
  };

  const handleBackToSite = () => {
    setIsAdminView(false);
    if (window.history.pushState) {
      window.history.pushState(null, '', '/');
    }
  };

  // If Admin View is Active, render Admin Portal
  if (isAdminView) {
    return <AdminPortal onBackToSite={handleBackToSite} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-amber-400 selection:text-slate-950">
      
      {/* Top Navbar */}
      <Navbar
        onRegisterClick={() => handleOpenRegister()}
        onPassLookupClick={() => setIsLookupOpen(true)}
        onAdminClick={handleSwitchToAdmin}
      />

      {/* Main Landing Page Content */}
      <main className="flex-1">
        <HeroSection onRegisterClick={(code) => {
          if (code) {
            const found = categories.find((c) => c.code === code);
            handleOpenRegister(found);
          } else {
            handleOpenRegister();
          }
        }} />

        <TrustBadges />

        <RaceCategoriesSection
          categories={categories}
          onSelectCategory={(cat) => handleOpenRegister(cat)}
        />

        <FinisherPerksSection />

        <RouteAndScheduleSection />

        <FaqSection />
      </main>

      {/* Sticky Mobile CTA for Social Ad Visitors */}
      <MobileStickyCTA onRegisterClick={() => handleOpenRegister()} />

      {/* Footer */}
      <Footer onAdminClick={handleSwitchToAdmin} />

      {/* Multi-Step Registration Modal */}
      <RegistrationModal
        isOpen={isRegisterModalOpen}
        onClose={() => setIsRegisterModalOpen(false)}
        categories={categories}
        initialCategory={selectedCategory}
        onSuccess={handleRegistrationSuccess}
      />

      {/* Confirmed Digital Pass Modal */}
      {activeSuccessCode && (
        <SuccessPassModal
          registrationCode={activeSuccessCode}
          onClose={() => {
            setActiveSuccessCode(null);
            // Clean URL query param if present
            if (window.history.pushState) {
              const cleanUrl = window.location.pathname;
              window.history.pushState(null, '', cleanUrl);
            }
          }}
        />
      )}

      {/* Pass Lookup Modal */}
      {isLookupOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="relative w-full max-w-md bg-white border border-slate-200 rounded-3xl p-6 shadow-2xl space-y-4">
            <button
              onClick={() => setIsLookupOpen(false)}
              className="absolute top-4 right-4 w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 flex items-center justify-center text-sm font-mono transition-colors"
            >
              ✕
            </button>
            <div className="space-y-1">
              <h3 className="font-bold text-slate-900 text-lg">Lookup Your Entry Pass</h3>
              <p className="text-xs text-slate-500">
                Enter your Registration Code (e.g. MX26-000001) to view or print your BIB ticket.
              </p>
            </div>
            <form onSubmit={handleLookupSubmit} className="space-y-3 pt-2">
              <input
                type="text"
                value={lookupCodeInput}
                onChange={(e) => setLookupCodeInput(e.target.value)}
                placeholder="MX26-000001"
                className="w-full bg-slate-50 border border-slate-300 rounded-xl p-3 text-sm text-slate-900 font-mono uppercase focus:outline-none focus:border-amber-500 focus:bg-white transition-all"
                required
              />
              <button
                type="submit"
                className="w-full py-3 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm rounded-xl transition-all shadow-md shadow-amber-500/20"
              >
                Find My Pass →
              </button>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
