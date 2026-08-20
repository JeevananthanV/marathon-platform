import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { useUTM } from '@/hooks/useUTM';
import { useRazorpay } from '@/hooks/useRazorpay';
import { RaceCategory, ParticipantData } from '@/types';

interface RegistrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  categories: RaceCategory[];
  initialCategory?: RaceCategory | null;
  onSuccess: (registrationCode: string) => void;
}

export const RegistrationModal: React.FC<RegistrationModalProps> = ({
  isOpen,
  onClose,
  categories,
  initialCategory,
  onSuccess,
}) => {
  const utm = useUTM();
  const { openCheckout } = useRazorpay();

  const [step, setStep] = useState<number>(1);
  const [selectedCategory, setSelectedCategory] = useState<RaceCategory | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState<ParticipantData>({
    full_name: '',
    email: '',
    phone_number: '',
    date_of_birth: '',
    gender: 'MALE',
    blood_group: 'O+',
    tshirt_size: 'M',
    emergency_contact_name: '',
    emergency_contact_phone: '',
    city: '',
    state: '',
  });

  const [termsAccepted, setTermsAccepted] = useState<boolean>(true);
  const [communicationConsent, setCommunicationConsent] = useState<boolean>(true);

  useEffect(() => {
    if (initialCategory) {
      setSelectedCategory(initialCategory);
    } else if (categories.length > 0 && !selectedCategory) {
      setSelectedCategory(categories[0]);
    }
  }, [initialCategory, categories]);

  if (!isOpen) return null;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const validateStep = (currentStep: number): boolean => {
    setError(null);
    if (currentStep === 1) {
      if (!selectedCategory) {
        setError('Please select a race category.');
        return false;
      }
      if (selectedCategory.slots_remaining <= 0) {
        setError('This category is fully booked. Please choose another tier.');
        return false;
      }
    } else if (currentStep === 2) {
      if (!formData.full_name.trim()) {
        setError('Please enter your full name.');
        return false;
      }
      if (!formData.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
        setError('Please enter a valid email address.');
        return false;
      }
      if (!formData.phone_number.match(/^\+?[0-9]{10,15}$/)) {
        setError('Please enter a valid 10-15 digit phone number.');
        return false;
      }
      if (!formData.date_of_birth) {
        setError('Please enter your date of birth.');
        return false;
      }
    } else if (currentStep === 3) {
      if (!formData.emergency_contact_name.trim()) {
        setError('Please provide an emergency contact name.');
        return false;
      }
      if (!formData.emergency_contact_phone.match(/^\+?[0-9]{10,15}$/)) {
        setError('Please enter a valid emergency contact phone number.');
        return false;
      }
    } else if (currentStep === 4) {
      if (!formData.city.trim() || !formData.state.trim()) {
        setError('Please enter your city and state.');
        return false;
      }
    } else if (currentStep === 5) {
      if (!termsAccepted) {
        setError('You must accept the terms & conditions and liability waiver.');
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (validateStep(step)) {
      setStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    setError(null);
    setStep((prev) => Math.max(1, prev - 1));
  };

  const handleProceedToPayment = async () => {
    if (!validateStep(5)) return;
    if (!selectedCategory) return;

    setSubmitting(true);
    setError(null);

    try {
      // 1. Server-side registration initiate & order creation
      const initResult = await api.initiateRegistration({
        category_id: selectedCategory.id,
        participant: formData,
        utm,
        terms_accepted: termsAccepted,
        communication_consent: communicationConsent,
      });

      // 2. Open Razorpay TEST MODE Checkout Modal
      openCheckout({
        keyId: initResult.razorpay_key_id,
        orderId: initResult.razorpay_order_id,
        amountInr: initResult.amount_inr,
        eventName: 'City Marathon 2026',
        description: `${selectedCategory.title} Registration`,
        participant: {
          name: formData.full_name,
          email: formData.email,
          phone: formData.phone_number,
        },
        onSuccess: async (rzpResponse) => {
          try {
            // 3. Server-side payment verification
            const verifyResult = await api.verifyPayment({
              razorpay_order_id: rzpResponse.razorpay_order_id,
              razorpay_payment_id: rzpResponse.razorpay_payment_id,
              razorpay_signature: rzpResponse.razorpay_signature,
            });

            onSuccess(verifyResult.registration_code);
          } catch (verifyErr: any) {
            setError(verifyErr.message || 'Payment verification failed on server.');
            setSubmitting(false);
          }
        },
        onFailure: (err) => {
          setError(err?.description || 'Payment was cancelled or failed. Please retry.');
          setSubmitting(false);
        },
        onDismiss: () => {
          setSubmitting(false);
        },
      });
    } catch (err: any) {
      setError(err.message || 'Failed to initiate registration.');
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-2xl space-y-6 my-8 transition-colors">
        
        {/* Modal Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 flex items-center justify-center text-sm font-mono transition-colors"
        >
          ✕
        </button>

        {/* Modal Header */}
        <div className="space-y-1 pr-8">
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 bg-amber-100 text-amber-800 rounded-full text-[10px] font-bold uppercase tracking-wider border border-amber-200">
            Step {step} of 6
          </div>
          <h2 className="text-xl sm:text-2xl font-black text-slate-900">
            {step === 1 && 'Select Race Category'}
            {step === 2 && 'Runner Information'}
            {step === 3 && 'Emergency Contact'}
            {step === 4 && 'Kit & Location Details'}
            {step === 5 && 'Consent & Event Waiver'}
            {step === 6 && 'Review & Checkout'}
          </h2>
        </div>

        {/* Step Progress Bar */}
        <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden border border-slate-200">
          <div
            className="bg-amber-500 h-full transition-all duration-300"
            style={{ width: `${(step / 6) * 100}%` }}
          />
        </div>

        {/* Error Banner */}
        {error && (
          <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700">
            ⚠️ <strong>Error:</strong> {error}
          </div>
        )}

        {/* STEP 1: CATEGORY SELECTION */}
        {step === 1 && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {categories.map((cat) => {
              const isSelected = selectedCategory?.id === cat.id;
              const isFull = cat.slots_remaining <= 0;
              return (
                <div
                  key={cat.id}
                  onClick={() => !isFull && setSelectedCategory(cat)}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between ${
                    isSelected
                      ? 'bg-amber-50 border-amber-500 ring-2 ring-amber-500/20'
                      : isFull
                      ? 'bg-slate-50 border-slate-200 opacity-50 cursor-not-allowed'
                      : 'bg-slate-50/70 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-white text-slate-800 border border-slate-200">
                        {cat.code}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {cat.slots_remaining} left
                      </span>
                    </div>
                    <div className="font-bold text-sm text-slate-900 mt-1">{cat.title}</div>
                    <div className="text-[11px] text-slate-500">Flag-off: {cat.start_time}</div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-slate-200 text-right">
                    <span className="text-base font-extrabold text-amber-600">₹{cat.price_inr}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* STEP 2: RUNNER DETAILS */}
        {step === 2 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="space-y-1 sm:col-span-2">
              <label className="text-slate-700 font-semibold">Full Name *</label>
              <input
                type="text"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                placeholder="e.g. Arjun Sharma"
                className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:border-amber-500 placeholder:text-slate-400"
              />
            </div>
            <div className="space-y-1">
              <label className="text-slate-700 font-semibold">Email Address *</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="arjun@example.com"
                className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:border-amber-500 placeholder:text-slate-400"
              />
            </div>
            <div className="space-y-1">
              <label className="text-slate-700 font-semibold">Phone Number *</label>
              <input
                type="tel"
                name="phone_number"
                value={formData.phone_number}
                onChange={handleChange}
                placeholder="+919876543210"
                className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:border-amber-500 placeholder:text-slate-400"
              />
            </div>
            <div className="space-y-1">
              <label className="text-slate-700 font-semibold">Date of Birth *</label>
              <input
                type="date"
                name="date_of_birth"
                value={formData.date_of_birth}
                onChange={handleChange}
                className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:border-amber-500"
              />
            </div>
            <div className="space-y-1">
              <label className="text-slate-700 font-semibold">Gender *</label>
              <select
                name="gender"
                value={formData.gender}
                onChange={handleChange}
                className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:border-amber-500"
              >
                <option value="MALE">Male</option>
                <option value="FEMALE">Female</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
          </div>
        )}

        {/* STEP 3: EMERGENCY CONTACT */}
        {step === 3 && (
          <div className="space-y-3 text-xs">
            <p className="text-slate-500">
              We notify this contact in case of race medical emergencies.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-slate-700 font-semibold">Contact Person Name *</label>
                <input
                  type="text"
                  name="emergency_contact_name"
                  value={formData.emergency_contact_name}
                  onChange={handleChange}
                  placeholder="e.g. Pooja Sharma (Parent/Spouse)"
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:border-amber-500 placeholder:text-slate-400"
                />
              </div>
              <div className="space-y-1">
                <label className="text-slate-700 font-semibold">Emergency Phone *</label>
                <input
                  type="tel"
                  name="emergency_contact_phone"
                  value={formData.emergency_contact_phone}
                  onChange={handleChange}
                  placeholder="+919876543211"
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:border-amber-500 placeholder:text-slate-400"
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: KIT & LOCATION */}
        {step === 4 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="space-y-1">
              <label className="text-slate-700 font-semibold">Blood Group *</label>
              <select
                name="blood_group"
                value={formData.blood_group}
                onChange={handleChange}
                className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:border-amber-500"
              >
                <option value="A+">A+</option>
                <option value="A-">A-</option>
                <option value="B+">B+</option>
                <option value="B-">B-</option>
                <option value="O+">O+</option>
                <option value="O-">O-</option>
                <option value="AB+">AB+</option>
                <option value="AB-">AB-</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-slate-700 font-semibold">T-Shirt Kit Size *</label>
              <select
                name="tshirt_size"
                value={formData.tshirt_size}
                onChange={handleChange}
                className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:border-amber-500"
              >
                <option value="XS">XS (Extra Small - 36")</option>
                <option value="S">S (Small - 38")</option>
                <option value="M">M (Medium - 40")</option>
                <option value="L">L (Large - 42")</option>
                <option value="XL">XL (Extra Large - 44")</option>
                <option value="XXL">XXL (Double XL - 46")</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-slate-700 font-semibold">City *</label>
              <input
                type="text"
                name="city"
                value={formData.city}
                onChange={handleChange}
                placeholder="Bengaluru"
                className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:border-amber-500 placeholder:text-slate-400"
              />
            </div>
            <div className="space-y-1">
              <label className="text-slate-700 font-semibold">State *</label>
              <input
                type="text"
                name="state"
                value={formData.state}
                onChange={handleChange}
                placeholder="Karnataka"
                className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:border-amber-500 placeholder:text-slate-400"
              />
            </div>
          </div>
        )}

        {/* STEP 5: CONSENT & WAIVER */}
        {step === 5 && (
          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-slate-600 space-y-2 max-h-32 overflow-y-auto">
              <p className="font-semibold text-slate-900">Liability Waiver:</p>
              <p>
                I confirm that I am medically fit to participate in the City Marathon 2026. I release the race organizers and sponsors from liability for any injuries or loss during the event. Registrations are non-transferable.
              </p>
            </div>
            <label className="flex items-start gap-2.5 cursor-pointer text-slate-700">
              <input
                type="checkbox"
                checked={termsAccepted}
                onChange={(e) => setTermsAccepted(e.target.checked)}
                className="mt-0.5 rounded border-slate-300 text-amber-500 focus:ring-amber-500"
              />
              <span>I agree to the Event Terms & Liability Waiver. *</span>
            </label>
            <label className="flex items-start gap-2.5 cursor-pointer text-slate-700">
              <input
                type="checkbox"
                checked={communicationConsent}
                onChange={(e) => setCommunicationConsent(e.target.checked)}
                className="mt-0.5 rounded border-slate-300 text-amber-500 focus:ring-amber-500"
              />
              <span>I consent to receiving race updates and digital passes via WhatsApp & SMS.</span>
            </label>
          </div>
        )}

        {/* STEP 6: REVIEW & CHECKOUT */}
        {step === 6 && selectedCategory && (
          <div className="space-y-4 text-xs">
            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-2 font-mono">
              <div className="flex justify-between">
                <span className="text-slate-500">Race Category:</span>
                <span className="text-slate-900 font-bold">{selectedCategory.title} ({selectedCategory.distance_km} KM)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Runner:</span>
                <span className="text-slate-700 font-semibold">{formData.full_name} ({formData.phone_number})</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">T-Shirt Kit Size:</span>
                <span className="text-slate-700 font-semibold">{formData.tshirt_size}</span>
              </div>
              <div className="flex justify-between items-baseline pt-2 border-t border-slate-200 font-sans">
                <span className="text-sm font-bold text-slate-900">Total Amount:</span>
                <span className="text-xl font-black text-amber-600">₹{selectedCategory.price_inr}</span>
              </div>
            </div>

            <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-[11px]">
              🔒 <strong>Razorpay TEST MODE:</strong> Simulated checkout active. No live credit card charges.
            </div>
          </div>
        )}

        {/* Modal Footer Controls */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-200">
          {step > 1 ? (
            <button
              onClick={handleBack}
              disabled={submitting}
              className="py-2.5 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 text-xs font-semibold transition-colors"
            >
              ← Back
            </button>
          ) : (
            <div />
          )}

          {step < 6 ? (
            <button
              onClick={handleNext}
              className="py-2.5 px-6 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs shadow-md shadow-amber-500/20 active:scale-95 transition-all"
            >
              Next Step →
            </button>
          ) : (
            <button
              onClick={handleProceedToPayment}
              disabled={submitting}
              className="py-3 px-6 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-black text-xs flex items-center gap-2 shadow-md shadow-emerald-600/20 active:scale-95 transition-all"
            >
              {submitting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <span>Pay ₹{selectedCategory?.price_inr} & Confirm Registration</span>
              )}
            </button>
          )}
        </div>

      </div>
    </div>
  );
};
