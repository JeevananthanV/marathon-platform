import { useState, useEffect } from 'react';
import { UTMParams } from '@/types';

const UTM_STORAGE_KEY = 'marathon_utm_attribution';

export function useUTM(): UTMParams {
  const [utm, setUtm] = useState<UTMParams>({});

  useEffect(() => {
    if (typeof window === 'undefined') return;

    try {
      // 1. Check if UTM already saved in sessionStorage
      const saved = sessionStorage.getItem(UTM_STORAGE_KEY);
      let parsedSaved: UTMParams = {};
      if (saved) {
        parsedSaved = JSON.parse(saved);
      }

      // 2. Parse current URL search params
      const searchParams = new URLSearchParams(window.location.search);
      const urlUtm: UTMParams = {};

      const source = searchParams.get('utm_source');
      const medium = searchParams.get('utm_medium');
      const campaign = searchParams.get('utm_campaign');
      const term = searchParams.get('utm_term');
      const content = searchParams.get('utm_content');

      if (source) urlUtm.utm_source = source;
      if (medium) urlUtm.utm_medium = medium;
      if (campaign) urlUtm.utm_campaign = campaign;
      if (term) urlUtm.utm_term = term;
      if (content) urlUtm.utm_content = content;

      // Capture referrer if available
      if (document.referrer && !parsedSaved.referrer) {
        urlUtm.referrer = document.referrer;
      }

      const mergedUtm: UTMParams = {
        ...parsedSaved,
        ...urlUtm,
      };

      // Set fallback defaults if completely direct
      if (!mergedUtm.utm_source) {
        mergedUtm.utm_source = 'direct';
      }

      // Persist to session storage
      sessionStorage.setItem(UTM_STORAGE_KEY, JSON.stringify(mergedUtm));
      setUtm(mergedUtm);
    } catch (e) {
      console.warn('Could not access sessionStorage for UTM persistence', e);
    }
  }, []);

  return utm;
}
