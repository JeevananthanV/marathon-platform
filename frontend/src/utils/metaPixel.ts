/**
 * Meta Pixel & Conversions API (CAPI) Client-Side Helper
 * 
 * Provides client-side tracking hooks that pass deterministic eventIDs
 * matching server-side CAPI dispatches for accurate deduplication.
 * Safely fails silently if Meta Pixel script is not loaded or blocked.
 */

declare global {
  interface Window {
    fbq?: (...args: any[]) => void;
    _fbq?: (...args: any[]) => void;
  }
}

export const trackPixelEvent = (
  eventName: string,
  parameters?: Record<string, any>,
  eventId?: string
): void => {
  try {
    if (typeof window !== "undefined" && typeof window.fbq === "function") {
      const options = eventId ? { eventID: eventId } : undefined;
      window.fbq("track", eventName, parameters || {}, options);
    }
  } catch {
    // Fail silently without interrupting UI execution
  }
};

export const metaTrackers = {
  pageView: (eventId?: string) => {
    trackPixelEvent("PageView", {}, eventId);
  },

  viewContent: (categoryCode: string, categoryTitle: string, priceInr: number, eventId?: string) => {
    trackPixelEvent(
      "ViewContent",
      {
        content_name: categoryTitle,
        content_category: "Marathon Race Category",
        content_ids: [categoryCode],
        content_type: "product",
        value: priceInr,
        currency: "INR",
      },
      eventId
    );
  },

  lead: (categoryTitle: string, priceInr: number, eventId?: string) => {
    trackPixelEvent(
      "Lead",
      {
        content_name: categoryTitle,
        content_category: "Marathon Lead",
        value: priceInr,
        currency: "INR",
      },
      eventId
    );
  },

  initiateCheckout: (categoryCode: string, categoryTitle: string, priceInr: number, eventId?: string) => {
    trackPixelEvent(
      "InitiateCheckout",
      {
        content_name: categoryTitle,
        content_ids: [categoryCode],
        value: priceInr,
        currency: "INR",
        num_items: 1,
      },
      eventId
    );
  },

  purchase: (registrationCode: string, paymentId: string, amountInr: number, categoryTitle: string, eventId?: string) => {
    const dedupId = eventId || `purchase_${registrationCode}_${paymentId}`;
    trackPixelEvent(
      "Purchase",
      {
        content_name: categoryTitle,
        value: amountInr,
        currency: "INR",
        order_id: registrationCode,
      },
      dedupId
    );
  },

  completeRegistration: (registrationCode: string, bibNumber?: string, amountInr?: number, eventId?: string) => {
    const dedupId = eventId || `complete_registration_${registrationCode}`;
    trackPixelEvent(
      "CompleteRegistration",
      {
        content_name: "Marathon Confirmed Registration",
        status: "CONFIRMED",
        value: amountInr,
        currency: "INR",
      },
      dedupId
    );
  },
};
