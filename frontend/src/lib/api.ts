// Typed client for the BurnoutAI API (proxied at /api in development).

const BASE = import.meta.env.VITE_API_URL ?? '/api'

export type Role = 'employee' | 'student' | 'general'

/** The six asked every day; the rest are optional and default to typical values server-side. */
export interface Drivers {
  sleep_hours: number
  work_hours_per_day: number
  after_hours_per_week: number
  workload: number
  can_disconnect: number
  support: number
  meetings_per_day?: number | null
  days_off_last_month?: number | null
  autonomy?: number | null
  recognition?: number | null
  role_type: Role
  remote_work: boolean
}
export type DailyKey = 'sleep_hours' | 'work_hours_per_day' | 'after_hours_per_week' | 'workload' | 'can_disconnect' | 'support'
export type DriverKey = DailyKey

export interface Contribution { feature: string; label: string; value: number | string; unit: string; impact: number }
export interface Lever { feature: string; label: string; change: string; expected_change: number }

export interface Prediction {
  score: number
  score_source: 'measured' | 'estimated'
  level: number
  label: string
  color: string
  measured: { personal: number; work: number; overall: number } | null
  burnout_pattern: string | null
  explanation: {
    base_score: number
    estimated_score: number
    interval: [number, number]
    contributions: Contribution[]
    unexplained: number | null
    summary: string
  }
  levers: Lever[]
  recommendations: string[]
  model: { version: string; training_source: string; mae: number; note: string }
}

export interface WhatIf { before: number; after: number; change: number; contributions_change: Contribution[] }

export interface DriverChange { feature: string; label: string; change: number }
export interface Forecast {
  status: 'insufficient_data' | 'improving' | 'stable' | 'rising'
  check_ins: number
  current: number | null
  slope_per_week: number | null
  horizon_weeks: number
  projected: number | null
  projected_interval: [number, number] | null
  weeks_to_threshold: number | null
  early_warning: boolean
  what_changed: DriverChange[]
  summary: string
}

export interface AssessmentRecord {
  id: number
  created_at: string
  score: number
  score_source: string
  measured_score: number | null
  estimated_score: number
  level: number
  burnout_pattern: string | null
}

export interface Question { id: string; text: string; options: { label: string; value: number }[] }
export interface Slider { id: DailyKey; label: string; unit: string; min: number; max: number; step: number }
export interface Instrument {
  questions: Question[]
  weekly: Question[]
  weekly_due: boolean
  sliders: Slider[]
  citation: string
  levels: { level: number; min: number; label: string; color: string }[]
}

export interface Persona {
  member_id: number
  title: string
  group: string
  org_kind: string
  role_type: Role
  score: number
  status: Forecast['status']
  early_warning: boolean
}

export interface Group { id: number; name: string }
export interface Org { id: number; name: string; kind: string; groups: Group[] }
export interface OrgSummary { id: number; name: string; kind: string; is_demo: boolean; role: string | null }

export interface Membership {
  org_id: number
  org_name: string
  org_kind: string
  role: 'owner' | 'admin' | 'member'
  group_id: number | null
  group_name: string | null
  sharing_since: string | null
}
export interface Me {
  user: { id: number; email: string; name: string; email_verified: boolean; reminders: boolean }
  member_id: number
  role_type: Role
  check_ins: number
  timezone: string
  today: { done: boolean; weekly_due: boolean; next_at: string | null }
  membership: Membership | null
}
export interface Invite { code: string; role: string; group_id: number | null; expires_at: string; uses: number; max_uses: number; revoked: boolean }
export interface InvitePreview { org_name: string; org_kind: string; role: string; group_id: number | null; groups: Group[]; min_group_size: number }
export interface OrgAdmin { org: Org; role: string; groups: { id: number; name: string; members: number }[]; admins: number; invites: Invite[] }
export interface Latest { created_at: string; drivers: Drivers; prediction: Prediction }
export interface DriverAgg { feature: string; label: string; avg_impact: number }
export interface TrendPoint { week_ending: string; respondents: number; avg_score: number | null }
export interface GroupInsight {
  group_id: number
  group_name: string
  member_count: number
  suppressed: boolean
  avg_score: number | null
  level_distribution: Record<string, number> | null
  pattern_distribution: Record<string, number> | null
  top_drivers: DriverAgg[] | null
  what_changed: DriverChange[] | null
  rising_count: number | null
  early_warning_count: number | null
  weekly_trend: TrendPoint[] | null
}
export interface OrgInsights {
  org_id: number
  org_name: string
  min_group_size: number
  respondents: number
  avg_score: number | null
  level_distribution: Record<string, number>
  top_drivers: DriverAgg[]
  rising_count: number | null
  early_warning_count: number | null
  groups: GroupInsight[]
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

function detail(body: unknown, status: number): string {
  const d = (body as { detail?: unknown } | null)?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg).replace(/^Value error, /, '')
  return `Request failed (${status})`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    credentials: 'include',
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) throw new ApiError(detail(await res.json().catch(() => null), res.status), res.status)
  return (res.status === 204 ? undefined : res.json()) as Promise<T>
}

const browserZone = () => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch {
    return 'UTC'
  }
}

const post = <T,>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
const del = <T,>(path: string) => request<T>(path, { method: 'DELETE' })

export const api = {
  instrument: () => request<Instrument>('/instrument'),
  predict: (drivers: Drivers, cbi_answers?: Record<string, number> | null) =>
    post<Prediction>('/predict', { drivers, cbi_answers: cbi_answers ?? null }),
  submit: (member_id: number, drivers: Drivers, cbi_answers?: Record<string, number> | null) =>
    post<Prediction>('/assessments', { member_id, drivers, cbi_answers: cbi_answers ?? null }),
  whatIf: (drivers: Drivers, changes: Partial<Record<DriverKey, number>>) => post<WhatIf>('/what-if', { drivers, changes }),
  // demo people (no account)
  history: (memberId: number) => request<AssessmentRecord[]>(`/members/${memberId}/assessments`),
  latest: (memberId: number) => request<Latest>(`/members/${memberId}/latest`),
  forecast: (memberId: number) => request<Forecast>(`/members/${memberId}/forecast`),
  personas: () => request<Persona[]>('/demo/personas'),

  // accounts
  signup: (body: { email: string; password: string; name: string; role_type: Role }) =>
    post<Me>('/auth/signup', { ...body, timezone: browserZone() }),
  login: (email: string, password: string) => post<Me>('/auth/login', { email, password, timezone: browserZone() }),
  logout: () => post<void>('/auth/logout'),
  me: () => request<Me>('/me'),
  verify: (code: string) => post<Me>('/auth/verify', { code }),
  resendCode: () => post<void>('/auth/verify/resend'),
  forgot: (email: string) => post<void>('/auth/forgot', { email }),
  reset: (email: string, code: string, password: string) => post<Me>('/auth/reset', { email, code, password }),
  changePassword: (current_password: string, new_password: string) => post<Me>('/me/password', { current_password, new_password }),
  updateProfile: (body: { role_type?: Role; reminders?: boolean }) => request<Me>('/me', { method: 'PATCH', body: JSON.stringify(body) }),
  setRoleType: (role_type: Role) => request<Me>('/me', { method: 'PATCH', body: JSON.stringify({ role_type }) }),
  exportUrl: `${BASE}/me/export`,
  deleteAccount: (password: string) => request<void>('/me', { method: 'DELETE', body: JSON.stringify({ password }) }),
  myCheckIn: (drivers: Drivers, cbi_answers?: Record<string, number> | null) =>
    post<Prediction>('/me/assessments', { drivers, cbi_answers: cbi_answers ?? null }),
  myHistory: () => request<AssessmentRecord[]>('/me/assessments'),
  myLatest: () => request<Latest>('/me/latest'),
  myForecast: () => request<Forecast>('/me/forecast'),
  startSharing: (groupId: number) => post<Me>(`/me/sharing?group_id=${groupId}`),
  stopSharing: () => del<Me>('/me/sharing'),
  leaveOrg: () => del<Me>('/me/membership'),

  // organisations
  orgs: () => request<OrgSummary[]>('/orgs'),
  org: (orgId: number) => request<Org>(`/orgs/${orgId}`),
  createOrg: (name: string, kind: 'company' | 'school', groups: string[]) => post<Org>('/orgs', { name, kind, groups }),
  insights: (orgId: number) => request<OrgInsights>(`/orgs/${orgId}/insights`),
  orgAdmin: (orgId: number) => request<OrgAdmin>(`/orgs/${orgId}/admin`),
  addGroup: (orgId: number, name: string) => post<Org>(`/orgs/${orgId}/groups`, { name }),
  createInvite: (orgId: number, body: { role: 'member' | 'admin'; group_id: number | null }) => post<Invite>(`/orgs/${orgId}/invites`, body),
  revokeInvite: (orgId: number, code: string) => del<void>(`/orgs/${orgId}/invites/${code}`),
  inviteEmails: (orgId: number, body: { emails: string[]; role: 'member' | 'admin'; group_id: number | null }) =>
    post<{ sent: number; invite: Invite }>(`/orgs/${orgId}/invites/email`, body),
  invite: (code: string) => request<InvitePreview>(`/invites/${code}`),
  acceptInvite: (code: string, group_id: number | null) => post<Me>(`/invites/${code}/accept`, { consent: true, group_id }),
}
