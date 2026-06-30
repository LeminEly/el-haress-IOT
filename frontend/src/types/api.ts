export type AccountRole = 'SUPER_ADMIN' | 'COMPANY';
export type AccountStatus = 'ACTIVE' | 'SUSPENDED';
export type AccountLanguage = 'fr' | 'ar' | 'en';
export type AlertSeverity = 'INFO' | 'WARNING' | 'CRITICAL' | 'EMERGENCY';
export type AlertStatus = 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED';
export type AlertCondition = 'GT' | 'GTE' | 'LT' | 'LTE';
export type AlertChannel = 'whatsapp' | 'sms' | 'email';
export type SensorStatus = 'normal' | 'warning' | 'critical' | 'offline';
export type BadgeTone = 'neutral' | 'normal' | 'warning' | 'critical' | 'offline';

export interface ApiEnvelope<T> {
  data: T;
  message?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface AccountProfile {
  id: string;
  phone_number: string;
  company_name: string;
  contact_email: string | null;
  language: AccountLanguage;
  role: AccountRole;
  status: AccountStatus;
  last_login_at: string | null;
}

export interface AccountSummary extends AccountProfile {
  created_at: string;
}

export interface Gateway {
  id: string;
  name: string;
  base_url: string;
  poll_interval_seconds: number;
  is_active: boolean;
  last_polled_at: string | null;
}

export interface Sensor {
  id: string;
  gateway_id: string;
  gateway_ref: string;
  hardware_id: string | null;
  label: string;
  kind: string;
  unit: string | null;
  is_active: boolean;
  last_seen_at: string | null;
  device_index: number | null;
  display_name: string;
  is_binary: boolean;
  online: boolean;
  critical_threshold: number | null;
  color: string | null;
}

export interface ReadingPoint {
  sensor_id: string;
  recorded_at: string;
  value: number;
}

export interface LatestReading {
  sensor_id: string;
  label: string;
  unit: string | null;
  value: number;
  recorded_at: string;
}

export interface DashboardSummary {
  sensors_total: number;
  sensors_active: number;
  offline_after_seconds: number;
  latest: LatestReading[];
}

export interface CompanyHealth {
  account_id: string;
  company_name: string;
  phone_number: string;
  status: AccountStatus;
  language: AccountLanguage;
  sensors_total: number;
  sensors_online: number;
  active_alerts: number;
  last_activity_at: string | null;
}

export interface PlatformOverview {
  companies_total: number;
  companies_active: number;
  companies_suspended: number;
  sensors_total: number;
  sensors_online: number;
  active_alerts: number;
  companies: CompanyHealth[];
}

export interface AlertRule {
  id: string;
  name: string;
  sensor_id: string | null;
  condition: AlertCondition;
  threshold: number;
  duration_seconds: number;
  cooldown_minutes: number;
  severity: AlertSeverity;
  channels: string[];
  is_active: boolean;
  created_at: string;
}

export interface Alert {
  id: string;
  alert_rule_id: string | null;
  sensor_id: string | null;
  severity: AlertSeverity;
  value: number;
  status: AlertStatus;
  triggered_at: string;
  acknowledged_at: string | null;
}

export interface LiveReading {
  sensor_id: string;
  value: number;
  recorded_at: string;
}
