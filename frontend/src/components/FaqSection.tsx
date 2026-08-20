import React, { useState } from 'react';

export const FaqSection: React.FC = () => {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const faqs = [
    {
      q: 'How do I receive my registration confirmation and BIB number?',
      a: 'Immediately upon completing your online payment, you will receive your unique Registration ID (e.g. MX26-000001) and allocated BIB number. A digital pass will be generated on-screen with instant WhatsApp & SMS confirmation.',
    },
    {
      q: 'When and where can I collect my Race Kit & T-Shirt?',
      a: 'Race kits (Dri-FIT T-shirt, RFID Timing Bib, Safety pins, and event guide) can be collected from the City Marathon Expo at Kanteerava Stadium on October 16 & 17, 2026 between 10:00 AM and 6:00 PM. Please bring your digital pass on your phone.',
    },
    {
      q: 'Can I transfer or cancel my marathon entry?',
      a: 'Marathon registrations are strictly non-refundable and non-transferable to ensure accurate emergency contact records and official timing chip validation.',
    },
    {
      q: 'Are there baggage storage and parking facilities available?',
      a: 'Yes, secure baggage counters with token tags and designated multi-level runner parking are available inside the stadium premises starting 04:30 AM on race day.',
    },
    {
      q: 'What payment modes are accepted during registration?',
      a: 'We accept all major UPI apps (Google Pay, PhonePe, Paytm), Credit/Debit Cards (Visa, Mastercard, RuPay), and Net Banking via Razorpay secure checkout.',
    },
  ];

  return (
    <section id="faqs" className="py-16 sm:py-24 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10 transition-colors">
      
      {/* Heading */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-semibold uppercase tracking-wider border border-amber-200">
          Got Questions?
        </div>
        <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
          Frequently Asked Questions
        </h2>
        <p className="text-slate-600 text-sm">
          Everything you need to know before stepping onto the starting line.
        </p>
      </div>

      {/* Accordion */}
      <div className="space-y-3">
        {faqs.map((faq, idx) => {
          const isOpen = openIndex === idx;
          return (
            <div
              key={idx}
              className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden transition-all"
            >
              <button
                onClick={() => setOpenIndex(isOpen ? null : idx)}
                className="w-full p-5 sm:p-6 text-left flex items-center justify-between gap-4 hover:bg-slate-50 transition-colors"
              >
                <span className="font-bold text-slate-900 text-sm sm:text-base">{faq.q}</span>
                <span
                  className={`text-amber-600 font-mono text-lg transition-transform duration-200 ${
                    isOpen ? 'rotate-45' : ''
                  }`}
                >
                  +
                </span>
              </button>

              {isOpen && (
                <div className="px-5 pb-5 sm:px-6 sm:pb-6 text-xs sm:text-sm text-slate-600 border-t border-slate-100 pt-4 leading-relaxed bg-white">
                  {faq.a}
                </div>
              )}
            </div>
          );
        })}
      </div>

    </section>
  );
};
