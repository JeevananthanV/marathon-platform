import { useState, useCallback } from 'react';

declare global {
  interface Window {
    Razorpay: any;
  }
}

interface OpenRazorpayOptions {
  keyId: string;
  orderId: string;
  amountInr: number;
  currency?: string;
  eventName?: string;
  description?: string;
  participant: {
    name: string;
    email: string;
    phone: string;
  };
  onSuccess: (response: {
    razorpay_payment_id: string;
    razorpay_order_id: string;
    razorpay_signature: string;
  }) => void;
  onFailure?: (error: any) => void;
  onDismiss?: () => void;
}

export function useRazorpay() {
  const [loading, setLoading] = useState<boolean>(false);

  const loadScript = (): Promise<boolean> => {
    return new Promise((resolve) => {
      if (typeof window === 'undefined') {
        resolve(false);
        return;
      }

      if (window.Razorpay) {
        resolve(true);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      script.onload = () => resolve(true);
      script.onerror = () => {
        console.error('Failed to load Razorpay checkout SDK script');
        resolve(false);
      };
      document.body.appendChild(script);
    });
  };

  const openCheckout = useCallback(
    async (options: OpenRazorpayOptions) => {
      setLoading(true);
      try {
        const isLoaded = await loadScript();
        if (!isLoaded) {
          throw new Error('Razorpay SDK could not be loaded. Please check your internet connection.');
        }

        const razorpayOptions = {
          key: options.keyId,
          amount: Math.round(options.amountInr * 100),
          currency: options.currency || 'INR',
          name: options.eventName || 'City Marathon 2026',
          description: options.description || 'Marathon Race Registration',
          order_id: options.orderId,
          prefill: {
            name: options.participant.name,
            email: options.participant.email,
            contact: options.participant.phone,
          },
          theme: {
            color: '#0284c7', // Sky-600
          },
          handler: (response: {
            razorpay_payment_id: string;
            razorpay_order_id: string;
            razorpay_signature: string;
          }) => {
            options.onSuccess(response);
          },
          modal: {
            ondismiss: () => {
              if (options.onDismiss) {
                options.onDismiss();
              }
            },
          },
        };

        const rzp = new window.Razorpay(razorpayOptions);

        rzp.on('payment.failed', (response: any) => {
          if (options.onFailure) {
            options.onFailure(response.error);
          }
        });

        rzp.open();
      } catch (err: any) {
        if (options.onFailure) {
          options.onFailure(err);
        }
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return { openCheckout, loading };
}
