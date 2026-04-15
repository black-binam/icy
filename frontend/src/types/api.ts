/**
 * Types partagés avec l'API ICY.
 *
 * Ces types miroitent les schémas Pydantic du backend (app/schemas/*).
 * Ils sont volontairement explicites (pas de `any`) et marqués readonly pour
 * les collections immuables côté client.
 */

export type UserRole = 'admin' | 'coordinator' | 'caregiver';

export interface User {
  id: number;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

/* =============== Référentiel métier =============== */

export interface Pathology {
  id: number;
  code: string;
  label: string;
  base_care_minutes: number;
  /** Coefficient de charge (> 0). */
  weight_coefficient: number;
  created_at: string;
  updated_at: string;
}

export interface PathologyUpsert {
  code: string;
  label: string;
  base_care_minutes: number;
  weight_coefficient: number;
}

export interface PatientPathology {
  pathology_id: number;
  pathology?: Pathology;
  frequency_per_week: number;
  extra_care_minutes: number;
}

export interface Patient {
  id: number;
  first_name: string;
  last_name: string;
  address: string;
  lat: number;
  lon: number;
  phone: string | null;
  notes: string | null;
  preferred_time_window_start: string | null;
  preferred_time_window_end: string | null;
  is_active: boolean;
  consent_given_at: string | null;
  pathologies: PatientPathology[];
  created_at: string;
  updated_at: string;
}

export interface PatientUpsert {
  first_name: string;
  last_name: string;
  address: string;
  lat: number;
  lon: number;
  phone?: string | null;
  notes?: string | null;
  preferred_time_window_start?: string | null;
  preferred_time_window_end?: string | null;
  is_active?: boolean;
  pathologies?: Array<{
    pathology_id: number;
    frequency_per_week: number;
    extra_care_minutes: number;
  }>;
}

export interface Caregiver {
  id: number;
  user_id: number;
  first_name: string;
  last_name: string;
  home_base_lat: number;
  home_base_lon: number;
  daily_capacity_minutes: number;
  skills: string[];
  created_at: string;
  updated_at: string;
}

export interface CaregiverUpsert {
  first_name: string;
  last_name: string;
  home_base_lat: number;
  home_base_lon: number;
  daily_capacity_minutes: number;
  skills: string[];
  /** Création d'un compte lié (admin only) */
  email?: string;
  password?: string;
}

/* =============== Tournées =============== */

export interface RouteStop {
  id: number;
  route_id: number;
  patient_id: number;
  patient?: Pick<Patient, 'id' | 'first_name' | 'last_name' | 'lat' | 'lon' | 'address'>;
  sequence: number;
  arrival_minutes: number;
  departure_minutes: number;
  distance_from_prev_m: number;
}

export interface Route {
  id: number;
  caregiver_id: number;
  caregiver?: Pick<Caregiver, 'id' | 'first_name' | 'last_name' | 'home_base_lat' | 'home_base_lon'>;
  date: string; // ISO date
  status: 'draft' | 'planned' | 'in_progress' | 'done' | 'cancelled';
  total_distance_m: number;
  total_duration_minutes: number;
  total_workload_minutes: number;
  stops: RouteStop[];
  created_at: string;
  updated_at: string;
}

/* =============== Optimisation =============== */

export interface OptimizeParams {
  date: string;
  alpha_distance: number;
  beta_balance: number;
  gamma_time: number;
  time_limit_seconds: number;
  caregiver_ids?: number[];
  patient_ids?: number[];
}

export interface OptimizeResult {
  routes: Route[];
  unassigned_patient_ids: number[];
  total_distance_m: number;
  workload_stddev: number;
  solve_time_ms: number;
}

/* =============== KPIs / dashboard =============== */

export interface DashboardKpis {
  active_caregivers: number;
  active_patients: number;
  today_routes: number;
  today_stops: number;
  workload_stddev_minutes: number;
  per_caregiver_workload: Array<{
    caregiver_id: number;
    caregiver_name: string;
    workload_minutes: number;
    capacity_minutes: number;
  }>;
}

/* =============== Pagination =============== */

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/* =============== Erreur API normalisée =============== */

export interface ApiError {
  detail: string | Array<{ loc: (string | number)[]; msg: string; type: string }>;
}
