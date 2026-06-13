export interface HospitalListItem {
  id: string;
  name: string;
  slug: string;
  plan: 'basic' | 'professional' | 'enterprise';
  is_active: boolean;
  is_expired: boolean;
  subscription_expires_at: string | null;
  created_at: string;
  staff_count: number;
  admin_email: string | null;
  admin_name: string | null;
}

export interface HospitalDetail extends HospitalListItem {
  address: string;
  phone: string;
  email: string;
  logo_url: string;
  registration_number: string;
  license_key: string;
  user_limit: number;
  updated_at: string;
  staff_breakdown: {
    total: number;
    by_role: Record<string, number>;
  };
  admin: {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    last_login: string;
    employee_id: string;
  } | null;
  stats: {
    patients: number;
    encounters_30d: number;
    invoices: number;
  };
}

export interface PlatformStats {
  total_hospitals: number;
  active_hospitals: number;
  total_staff: number;
  total_patients: number;
  total_encounters: number;
  total_invoices: number;
  patients_30d: number;
  onboarding_30d: number;
}

export interface DashboardKpi {
  count: number;
  growth: string;
}

export interface ActiveUsersKpi {
  count: number;
  percentage: number;
}

export interface StorageUsedKpi {
  used: string;
  total: string;
  percentage: number;
}

export interface DashboardOverviewKpis {
  total_users: DashboardKpi;
  active_users: ActiveUsersKpi;
  departments: DashboardKpi;
  roles: DashboardKpi;
  system_uptime: { count: string; growth: string };
  storage_used: StorageUsedKpi;
}

export interface ModuleStatus {
  name: string;
  label: string;
  status: string;
  is_critical: boolean;
  hospital_id: string | null;
  updated_at?: string;
}

export interface DashboardStorage {
  storage_used_gb: number;
  storage_total_gb: number;
  database_status: string;
  last_backup: string | null;
  next_backup: string | null;
  [key: string]: any;
}

export interface LicenseInfo {
  edition: string;
  valid_from: string;
  valid_till: string;
  is_active: boolean;
  [key: string]: any;
}

export interface SystemInfo {
  python_version: string;
  django_version: string;
  server_time: string;
  [key: string]: any;
}

export interface SecurityOverview {
  [key: string]: any;
}

export interface DashboardOverview {
  kpis: DashboardOverviewKpis;
  module_status: ModuleStatus[];
  database_storage: DashboardStorage;
  license_info: LicenseInfo;
  system_info: SystemInfo;
  security_overview: SecurityOverview;
}

export interface ChartPoint {
  date: string;
  logins: number;
  transactions: number;
  errors: number;
}

export interface UserActivityEntry {
  username: string;
  email: string;
  role: string;
  last_active: string | null;
  login_count: number;
}

export interface AuditCategory {
  category: string;
  count: number;
}

export interface AuditLogEntry {
  id: string;
  event_type: string;
  description: string;
  author_name: string;
  created_at: string;
}

export interface DashboardActivity {
  system_overview_chart: ChartPoint[];
  user_activity: UserActivityEntry[];
  audit_summary: {
    total_logs: number;
    by_category: AuditCategory[];
    recent: AuditLogEntry[];
  };
}

export interface SystemAlert {
  id: string;
  severity: string;
  title: string;
  description: string;
  is_resolved: boolean;
  created_at: string;
  resolved_at: string | null;
  hospital_id: string | null;
}

export interface RecentActivity {
  id: string;
  event_type: string;
  description: string;
  author_name: string;
  hospital_name: string;
  created_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface DashboardAlerts {
  system_alerts: SystemAlert[];
  recent_activities: RecentActivity[];
}
