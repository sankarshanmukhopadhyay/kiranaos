/**
 * api.ts — Typed API client for all KiranaOS backend endpoints.
 * Uses the Vite dev proxy (/api → localhost:8000) in development.
 * In production, set VITE_API_BASE to your backend origin.
 */

const BASE = import.meta.env.VITE_API_BASE ?? "";

// ── Types (mirror backend schemas) ───────────────────────────────────────────

export type OrderStatus = "pending" | "packed" | "delivered" | "cancelled" | "needs_review";
export type MessageType = "text" | "image" | "voice";

export interface OrderItem {
  id:         number;
  name:       string;
  quantity:   number;
  unit:       string;
  confidence: number;  // 0–1; used to highlight uncertain parses
}

export interface Customer {
  id:             number;
  name:           string;
  phone:          string;
  building:       string | null;
  language_hint:  string | null;
  credit_balance: number;
  last_order_at:  string | null;
  dormant:        boolean;
}

export interface Order {
  id:           number;
  status:       OrderStatus;
  amount_due:   number;
  is_credit:    boolean;
  notes:        string | null;
  created_at:   string;
  updated_at:   string;
  delivered_at: string | null;
  customer:     Customer;
  items:        OrderItem[];
}

export interface DashboardSummary {
  pending:           number;
  packed:            number;
  delivered_today:   number;
  needs_review:      number;
  dormant_customers: number;
  total_credit:      number;
}

export interface DailyMetric {
  day:     string;
  orders:  number;
  revenue: number;
}

export interface TopItem {
  name:           string;
  count:          number;
  total_quantity: number;
}

export interface InputMethodStat {
  message_type: string;
  count:        number;
}

export interface LedgerEntry {
  id:         number;
  amount:     number;
  reason:     string;
  created_at: string;
}

// ── HTTP helper ────────────────────────────────────────────────────────────────

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── API surface ────────────────────────────────────────────────────────────────

export const api = {
  // Dashboard
  summary: () =>
    req<DashboardSummary>("/api/dashboard/summary"),

  // Orders
  orders: (params?: { status?: OrderStatus; customer_id?: number }) => {
    const qs = new URLSearchParams();
    if (params?.status)      qs.set("status", params.status);
    if (params?.customer_id) qs.set("customer_id", String(params.customer_id));
    return req<Order[]>(`/api/orders?${qs}`);
  },
  order: (id: number) =>
    req<Order>(`/api/orders/${id}`),
  setStatus: (id: number, status: OrderStatus) =>
    req<Order>(`/api/orders/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
  setAmount: (id: number, amount_due: number, is_credit: boolean) =>
    req<Order>(`/api/orders/${id}/amount`, { method: "PATCH", body: JSON.stringify({ amount_due, is_credit }) }),

  // Customers
  customers: (dormant_only = false) =>
    req<Customer[]>(`/api/customers?dormant_only=${dormant_only}`),
  createCustomer: (data: { name: string; phone: string; building?: string }) =>
    req<Customer>("/api/customers", { method: "POST", body: JSON.stringify(data) }),
  adjustCredit: (customer_id: number, amount: number, reason: string) =>
    req<Customer>(`/api/customers/${customer_id}/credit`, {
      method: "POST",
      body: JSON.stringify({ amount, reason }),
    }),
  ledger: (customer_id: number) =>
    req<LedgerEntry[]>(`/api/customers/${customer_id}/ledger`),

  // Ingest (demo / manual)
  ingest: (payload: {
    phone: string; customer_name?: string; building?: string;
    message_type?: MessageType; text?: string;
  }) => req<Order>("/api/ingest/messages", { method: "POST", body: JSON.stringify(payload) }),

  // Analytics
  daily: (days = 7) =>
    req<DailyMetric[]>(`/api/analytics/daily?days=${days}`),
  topItems: (days = 30, limit = 10) =>
    req<TopItem[]>(`/api/analytics/top-items?days=${days}&limit=${limit}`),
  inputMethods: (days = 30) =>
    req<InputMethodStat[]>(`/api/analytics/input-methods?days=${days}`),
};
