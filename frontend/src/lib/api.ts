import {
  HealthResponse,
  RaceCategory,
  RegistrationInitiateRequest,
  RegistrationInitiateResponse,
  PaymentVerificationRequest,
  PaymentVerificationResponse,
  RegistrationDetail,
  AdminDashboardStats,
  AdminLeadsResponse,
  AdminLeadItem,
  AdminRegistrationsResponse,
  AdminAnalyticsResponse,
  LeadStatus,
} from '@/types';

// Safely obtain base URL in Vite runtime (or default to empty string for relative proxying)
const getApiBaseUrl = (): string => {
  try {
    if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
      return import.meta.env.VITE_API_BASE_URL;
    }
  } catch {
    // Fallback if import.meta is not evaluated
  }
  return '';
};

export const API_BASE_URL = getApiBaseUrl();

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl ? baseUrl.replace(/\/+$/, '') : '';
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = this.baseUrl ? `${this.baseUrl}${cleanEndpoint}` : cleanEndpoint;

    const headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options?.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errorData: any;
        try {
          errorData = await response.json();
        } catch {
          errorData = { message: response.statusText };
        }
        
        const errorMessage =
          errorData.detail ||
          errorData.message ||
          errorData.error ||
          (typeof errorData === 'string' ? errorData : `HTTP error ${response.status}`);
        
        throw new Error(errorMessage);
      }

      return await response.json();
    } catch (error: any) {
      console.error(`API Request Error [${endpoint}]:`, error);
      throw error;
    }
  }

  /**
   * Health check endpoint
   */
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/api/health');
  }

  /**
   * List all active marathon race categories (5K, 10K, 21K)
   */
  async getCategories(): Promise<RaceCategory[]> {
    return this.request<RaceCategory[]>('/api/v1/categories');
  }

  /**
   * Get single category by ID or Code
   */
  async getCategory(categoryId: string): Promise<RaceCategory> {
    return this.request<RaceCategory>(`/api/v1/categories/${categoryId}`);
  }

  /**
   * Initiate registration and generate Razorpay TEST MODE order
   */
  async initiateRegistration(payload: RegistrationInitiateRequest): Promise<RegistrationInitiateResponse> {
    return this.request<RegistrationInitiateResponse>('/api/v1/registrations/initiate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Verify Razorpay payment signature server-side
   */
  async verifyPayment(payload: PaymentVerificationRequest): Promise<PaymentVerificationResponse> {
    return this.request<PaymentVerificationResponse>('/api/v1/payments/verify', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Fetch confirmed registration details & digital pass
   */
  async getRegistration(registrationCode: string): Promise<RegistrationDetail> {
    return this.request<RegistrationDetail>(`/api/v1/registrations/${registrationCode}`);
  }

  // ==========================================
  // PHASE 4: ADMIN DASHBOARD & ANALYTICS APIS
  // ==========================================

  /**
   * Get admin dashboard overview stats
   */
  async getAdminDashboard(adminKey: string): Promise<AdminDashboardStats> {
    return this.request<AdminDashboardStats>('/api/v1/admin/dashboard', {
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }

  /**
   * Query leads with filtering and search
   */
  async getAdminLeads(
    adminKey: string,
    params?: {
      search?: string;
      status?: string;
      utm_source?: string;
      utm_campaign?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<AdminLeadsResponse> {
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.status) query.set('status', params.status);
    if (params?.utm_source) query.set('utm_source', params.utm_source);
    if (params?.utm_campaign) query.set('utm_campaign', params.utm_campaign);
    if (params?.page) query.set('page', params.page.toString());
    if (params?.page_size) query.set('page_size', params.page_size.toString());

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<AdminLeadsResponse>(`/api/v1/admin/leads${qs}`, {
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }

  /**
   * Update lead status (e.g. NEW -> CONTACTED -> REGISTERED -> CONVERTED -> LOST)
   */
  async updateLeadStatus(
    adminKey: string,
    leadId: string,
    status: LeadStatus
  ): Promise<AdminLeadItem> {
    return this.request<AdminLeadItem>(`/api/v1/admin/leads/${leadId}/status`, {
      method: 'PATCH',
      headers: { 'X-Admin-API-Key': adminKey },
      body: JSON.stringify({ status }),
    });
  }

  /**
   * Query registrations with filters, sorting, and pagination
   */
  async getAdminRegistrations(
    adminKey: string,
    params?: {
      search?: string;
      category?: string;
      status?: string;
      payment_status?: string;
      utm_source?: string;
      utm_campaign?: string;
      sort_by?: string;
      sort_order?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<AdminRegistrationsResponse> {
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.category) query.set('category', params.category);
    if (params?.status) query.set('status', params.status);
    if (params?.payment_status) query.set('payment_status', params.payment_status);
    if (params?.utm_source) query.set('utm_source', params.utm_source);
    if (params?.utm_campaign) query.set('utm_campaign', params.utm_campaign);
    if (params?.sort_by) query.set('sort_by', params.sort_by);
    if (params?.sort_order) query.set('sort_order', params.sort_order);
    if (params?.page) query.set('page', params.page.toString());
    if (params?.page_size) query.set('page_size', params.page_size.toString());

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<AdminRegistrationsResponse>(`/api/v1/admin/registrations${qs}`, {
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }

  /**
   * Get conversion funnel & attribution analytics
   */
  async getAdminAnalytics(adminKey: string): Promise<AdminAnalyticsResponse> {
    return this.request<AdminAnalyticsResponse>('/api/v1/admin/analytics', {
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }

  /**
   * Get direct CSV download link with auth token query param
   */
  getExportLeadsUrl(adminKey: string): string {
    const base = this.baseUrl ? this.baseUrl : '';
    return `${base}/api/v1/admin/export/leads?admin_key=${encodeURIComponent(adminKey)}`;
  }

  /**
   * Get direct registrations CSV download link with auth token query param
   */
  getExportRegistrationsUrl(adminKey: string): string {
    const base = this.baseUrl ? this.baseUrl : '';
    return `${base}/api/v1/admin/export/registrations?admin_key=${encodeURIComponent(adminKey)}`;
  }

  /**
   * Demo reset (testing environments only)
   */
  async resetDemoData(adminKey: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>('/api/v1/admin/demo-reset', {
      method: 'POST',
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }

  // ==========================================
  // PHASE 5: ZOHO CRM INTEGRATION APIS
  // ==========================================

  /**
   * Get Zoho CRM synchronization status and health
   */
  async getZohoStatus(adminKey: string): Promise<any> {
    return this.request<any>('/api/v1/admin/zoho/status', {
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }

  /**
   * Manually trigger Zoho sync for single registration
   */
  async syncZohoRegistration(adminKey: string, registrationId: string): Promise<any> {
    return this.request<any>(`/api/v1/admin/zoho/sync/${registrationId}`, {
      method: 'POST',
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }

  /**
   * Retry all failed or pending Zoho CRM synchronizations
   */
  async retryFailedZoho(adminKey: string, limit: number = 50): Promise<any> {
    return this.request<any>(`/api/v1/admin/zoho/retry-failed?limit=${limit}`, {
      method: 'POST',
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }

  // ==========================================
  // PHASE 6: WHATSAPP AUTOMATION APIS
  // ==========================================

  /**
   * Get WhatsApp communication delivery statistics
   */
  async getWhatsAppStats(adminKey: string): Promise<any> {
    return this.request<any>('/api/v1/admin/whatsapp/stats', {
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }

  /**
   * Query WhatsApp message ledger with filters and pagination
   */
  async getWhatsAppMessages(
    adminKey: string,
    params?: {
      registration_id?: string;
      phone_number?: string;
      message_type?: string;
      status?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<any> {
    const query = new URLSearchParams();
    if (params?.registration_id) query.set('registration_id', params.registration_id);
    if (params?.phone_number) query.set('phone_number', params.phone_number);
    if (params?.message_type) query.set('message_type', params.message_type);
    if (params?.status) query.set('status', params.status);
    if (params?.page) query.set('page', params.page.toString());
    if (params?.page_size) query.set('page_size', params.page_size.toString());

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<any>(`/api/v1/admin/whatsapp/messages${qs}`, {
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }

  /**
   * Retry individual failed WhatsApp message
   */
  async retryWhatsAppMessage(adminKey: string, messageId: string): Promise<any> {
    return this.request<any>(`/api/v1/admin/whatsapp/messages/${messageId}/retry`, {
      method: 'POST',
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }

  /**
   * Retry all failed WhatsApp messages
   */
  async retryAllFailedWhatsApp(adminKey: string, limit: number = 50): Promise<any> {
    return this.request<any>(`/api/v1/admin/whatsapp/retry-failed?limit=${limit}`, {
      method: 'POST',
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }

  /**
   * Process due marathon reminders
   */
  async triggerProcessDueReminders(adminKey: string, reminderType?: string, referenceDate?: string): Promise<any> {
    const query = new URLSearchParams();
    if (reminderType) query.set('reminder_type', reminderType);
    if (referenceDate) query.set('reference_date', referenceDate);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<any>(`/api/v1/whatsapp/reminders/process-due${qs}`, {
      method: 'POST',
      headers: { 'X-Admin-API-Key': adminKey },
    });
  }
}

export const api = new ApiClient(API_BASE_URL);

