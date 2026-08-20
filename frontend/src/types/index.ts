// Race Category Interface
export interface RaceCategory {
  id: string;
  title: string;
  code: string;
  distance_km: number;
  price_inr: number;
  max_capacity: number;
  current_count: number;
  slots_remaining: number;
  bib_prefix: string;
  min_age: number;
  start_time: string;
  is_active: boolean;
}

// Health Response
export interface HealthResponse {
  status: string;
  version: string;
  service: string;
  timestamp?: string;
}

// UTM Attribution
export interface UTMParams {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
  referrer?: string;
}

// Participant Input Data
export interface ParticipantData {
  full_name: string;
  email: string;
  phone_number: string;
  date_of_birth: string;
  gender: 'MALE' | 'FEMALE' | 'OTHER';
  blood_group: string;
  tshirt_size: 'XS' | 'S' | 'M' | 'L' | 'XL' | 'XXL';
  emergency_contact_name: string;
  emergency_contact_phone: string;
  city: string;
  state: string;
}

// Registration Request Payload
export interface RegistrationInitiateRequest {
  category_id: string;
  participant: ParticipantData;
  utm?: UTMParams;
  terms_accepted?: boolean;
  communication_consent?: boolean;
}

export type RegistrationPayload = RegistrationInitiateRequest;

// Registration Initiation Response
export interface RegistrationInitiateResponse {
  registration_id: string;
  registration_code: string;
  razorpay_order_id: string;
  amount_inr: number;
  currency: string;
  razorpay_key_id: string;
}

// Payment Verification Payload
export interface PaymentVerifyPayload {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export type PaymentVerificationRequest = PaymentVerifyPayload;

// Payment Verification Response
export interface PaymentVerifyResponse {
  success: boolean;
  registration_code: string;
  bib_number: string;
  status: string;
  message: string;
}

export type PaymentVerificationResponse = PaymentVerifyResponse;

// Digital Pass / Registration Details Response
export interface RegistrationDetailsResponse {
  id: string;
  registration_code: string;
  status: string;
  bib_number?: string;
  confirmed_at?: string;
  created_at: string;
  participant: ParticipantData & { id: string };
  category: RaceCategory;
}

export type RegistrationDetail = RegistrationDetailsResponse;

// Phase 4 & 5 Admin Dashboard & Analytics Types
export interface AdminCategoryMetric {
  code: string;
  title: string;
  max_capacity: number;
  current_count: number;
  slots_remaining: number;
  fill_percentage: number;
  paid_count: number;
  price_inr: number;
  revenue_inr: number;
}

export interface ZohoStatusSummary {
  mode: string;
  configured: boolean;
  status: string;
  synced_count: number;
  pending_count: number;
  failed_count: number;
  last_sync_attempt?: string;
  health: Record<string, any>;
}

export interface ZohoSyncResponse {
  status: string;
  registration_code?: string;
  zoho_record_id?: string;
  action?: string;
  mock?: boolean;
  error?: string;
}

export interface ZohoRetryResponse {
  total_processed: number;
  successful: number;
  failed: number;
  details: any[];
}

// Phase 6 WhatsApp Communication Types
export interface WhatsAppStatsSummary {
  total_messages: number;
  pending_count: number;
  sent_count: number;
  delivered_count: number;
  read_count: number;
  failed_count: number;
  provider_health: Record<string, any>;
}

export interface WhatsAppMessageItem {
  id: string;
  registration_id?: string;
  participant_id?: string;
  phone_number: string;
  message_type: string;
  template_name: string;
  message_content?: string;
  provider: string;
  provider_message_id?: string;
  idempotency_key: string;
  status: 'PENDING' | 'SENT' | 'DELIVERED' | 'READ' | 'FAILED';
  created_at: string;
  sent_at?: string;
  delivered_at?: string;
  read_at?: string;
  failed_at?: string;
  error_message?: string;
  retry_count: number;
}

export interface WhatsAppMessageListResponse {
  total: number;
  page: number;
  page_size: number;
  items: WhatsAppMessageItem[];
}

export interface WhatsAppRetryResponse {
  total_processed: number;
  successful: number;
  failed: number;
  details: any[];
}

export interface AdminDashboardStats {
  event_name: string;
  total_leads: number;
  total_registrations: number;
  paid_registrations: number;
  pending_payments: number;
  failed_payments: number;
  revenue_inr: number;
  average_order_value_inr: number;
  paid_participants_count: number;
  categories: AdminCategoryMetric[];
  recent_registrations: Array<{
    registration_id: string;
    registration_code: string;
    bib_number?: string;
    status: string;
    category: string;
    category_code: string;
    participant_name: string;
    email: string;
    phone: string;
    amount_inr: number;
    payment_status: string;
    zoho_sync_status?: string;
    created_at: string;
  }>;
  integrations_summary: Record<string, { SUCCESS: number; FAILED: number }>;
  zoho_summary?: ZohoStatusSummary;
  whatsapp_summary?: WhatsAppStatsSummary;
}

export type LeadStatus = 'NEW' | 'CONTACTED' | 'REGISTERED' | 'PAYMENT_PENDING' | 'CONVERTED' | 'LOST';

export interface AdminLeadItem {
  id: string;
  name: string;
  email: string;
  phone: string;
  city: string;
  state: string;
  category_code?: string;
  category_title?: string;
  lead_status: LeadStatus;
  payment_status: string;
  registration_status: string;
  registration_code?: string;
  amount_inr: number;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  zoho_sync_status?: string;
  zoho_lead_id?: string;
  created_at: string;
}

export interface AdminLeadsResponse {
  total: number;
  page: number;
  page_size: number;
  items: AdminLeadItem[];
}

export interface AdminRegistrationItem {
  registration_id: string;
  registration_code: string;
  bib_number?: string;
  status: string;
  category_code: string;
  category_title: string;
  participant_name: string;
  email: string;
  phone: string;
  city: string;
  amount_inr: number;
  payment_status: string;
  razorpay_payment_id?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  zoho_sync_status?: string;
  zoho_lead_id?: string;
  zoho_last_sync_attempt?: string;
  created_at: string;
  confirmed_at?: string;
}

export interface AdminRegistrationsResponse {
  total: number;
  page: number;
  page_size: number;
  items: AdminRegistrationItem[];
}

export interface FunnelMetrics {
  total_leads: number;
  total_registered: number;
  total_paid: number;
  lead_to_reg_rate_pct: number;
  reg_to_paid_rate_pct: number;
  overall_conversion_rate_pct: number;
}

export interface CategoryAnalytics {
  category_code: string;
  category_title: string;
  registered_count: number;
  paid_count: number;
  revenue_inr: number;
  share_pct: number;
}

export interface UtmSourceAnalytics {
  source: string;
  leads_count: number;
  registered_count: number;
  paid_count: number;
  conversion_rate_pct: number;
  revenue_inr: number;
}

export interface RevenueMetrics {
  total_revenue_inr: number;
  paid_participants_count: number;
  average_order_value_inr: number;
}

export interface AdminAnalyticsResponse {
  funnel: FunnelMetrics;
  categories: CategoryAnalytics[];
  utm_sources: UtmSourceAnalytics[];
  revenue: RevenueMetrics;
}
