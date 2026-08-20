import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { RegistrationDetail } from '@/types';

interface SuccessPassModalProps {
  registrationCode: string;
  onClose: () => void;
}

export const SuccessPassModal: React.FC<SuccessPassModalProps> = ({
  registrationCode,
  onClose,
}) => {
  const [data, setData] = useState<RegistrationDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await api.getRegistration(registrationCode);
        setData(res);
      } catch (e: any) {
        setError(e.message || 'Unable to fetch registration pass.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [registrationCode]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-lg bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-2xl space-y-6 my-8 transition-colors">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 flex items-center justify-center text-sm font-mono transition-colors"
        >
          ✕
        </button>

        {loading && (
          <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-500">
            <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs">Generating your official runner pass...</span>
          </div>
        )}

        {error && (
          <div className="py-8 text-center space-y-3">
            <div className="text-3xl">⚠️</div>
            <h3 className="font-bold text-slate-900 text-base">Pass Not Found</h3>
            <p className="text-xs text-rose-600">{error}</p>
          </div>
        )}

        {data && (
          <div className="space-y-6">
            
            {/* Top Confirmed Header */}
            <div className="text-center space-y-1">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-100 text-emerald-800 rounded-full text-[10px] font-bold uppercase tracking-wider border border-emerald-200">
                ✓ Registration Confirmed
              </div>
              <h2 className="text-2xl font-black text-slate-900">You're On The Starting Line!</h2>
              <p className="text-slate-600 text-xs">
                Your payment is verified. Present this digital pass at the Bib Expo.
              </p>
            </div>

            {/* Digital Pass Ticket Card */}
            <div className="bg-white border-2 border-amber-400 rounded-2xl overflow-hidden shadow-lg">
              
              {/* Ticket Ribbon */}
              <div className="bg-amber-500 p-4 flex items-center justify-between text-slate-950 font-black">
                <div>
                  <div className="text-[10px] uppercase tracking-widest opacity-80">Official Entry Pass</div>
                  <div className="text-sm font-black">City Marathon 2026</div>
                </div>
                <div className="px-2.5 py-1 bg-slate-950 text-amber-400 font-mono text-xs rounded-md">
                  {data.category.code}
                </div>
              </div>

              {/* Ticket Body */}
              <div className="p-5 space-y-5">
                
                {/* BIB Number */}
                <div className="text-center bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1">
                  <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
                    Assigned BIB Number
                  </div>
                  <div className="text-4xl sm:text-5xl font-black text-slate-900 font-mono tracking-wider">
                    {data.bib_number || 'ASSIGNED'}
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono">
                    Reg ID: <strong className="text-slate-800">{data.registration_code}</strong>
                  </div>
                </div>

                {/* Details Table */}
                <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50 p-3.5 rounded-xl border border-slate-200 font-mono">
                  <div>
                    <span className="text-slate-500 block text-[10px]">Runner Name</span>
                    <span className="text-slate-900 font-bold">{data.participant.full_name}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Race Tier</span>
                    <span className="text-amber-700 font-bold">{data.category.title}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Flag-Off</span>
                    <span className="text-slate-800">{data.category.start_time}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">T-Shirt Size</span>
                    <span className="text-slate-800">{data.participant.tshirt_size}</span>
                  </div>
                </div>

                {/* Barcode Simulation */}
                <div className="pt-1 text-center space-y-1.5">
                  <div className="inline-flex gap-1 h-7 items-center opacity-75">
                    {Array.from({ length: 32 }).map((_, i) => (
                      <div
                        key={i}
                        className="bg-slate-800 rounded-sm"
                        style={{
                          width: `${(i % 3 === 0 ? 3 : i % 2 === 0 ? 2 : 1)}px`,
                          height: '100%',
                        }}
                      />
                    ))}
                  </div>
                  <div className="text-[9px] text-slate-500 font-mono">
                    Scan for automated bib chip calibration at Expo counter
                  </div>
                </div>

              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => window.print()}
                className="flex-1 py-3 px-4 rounded-xl bg-white hover:bg-slate-50 border border-slate-300 text-slate-800 font-semibold text-xs transition-colors flex items-center justify-center gap-1.5 shadow-sm"
              >
                🖨️ Print Pass
              </button>
              <button
                onClick={onClose}
                className="flex-1 py-3 px-4 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-extrabold text-xs transition-colors flex items-center justify-center shadow-md shadow-amber-500/20"
              >
                Done
              </button>
            </div>

          </div>
        )}

      </div>
    </div>
  );
};
