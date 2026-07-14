/**
 * api.ts — Typed API client for all KiranaOS backend endpoints.
 * Uses the Vite dev proxy (/api → localhost:8000) in development.
 * In production, set VITE_API_BASE to your backend origin.
 */

const BASE = import.meta.env.VITE_API_BASE ?? "";
const TOKEN_KEY = "kiranaos.token";

export function setAuthToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY);
}

// ── Types (mirror backend schemas) ───────────────────────────────────────────

export type OrderStatus = "pending" | "packed" | "delivered" | "cancelled" | "needs_review";
export type MessageType = "text" | "image" | "voice";
export type DeliveryStatus = "assigned" | "picked_up" | "delivered" | "failed";

export interface OrderItem {
  id:         number;
  name:       string;
  quantity:   number;
  unit:       string;
  confidence: number;  // 0–1; used to highlight uncertain parses
  product_id: number | null;
  substitution_for_item_id: number | null;
  notes: string | null;
}

export interface Customer {
  id:             number;
  name:           string;
  phone:          string;
  building:       string | null;
  address:        string | null;
  language_hint:  string | null;
  credit_balance: number;
  last_order_at:  string | null;
  dormant:        boolean;
}

export interface InboundMessage {
  id: number;
  source: string;
  external_message_id: string | null;
  message_type: MessageType;
  raw_text: string | null;
  extracted_text: string | null;
  media_type: string | null;
  language: string | null;
  parse_status: "pending" | "parsed" | "needs_review" | "failed";
  parse_failure_reason: string | null;
  received_at: string;
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
  message:      InboundMessage | null;
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

export interface Operator {
  id: number;
  store_id: number;
  username: string;
  role: "owner" | "manager" | "staff";
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: "bearer";
  operator: Operator;
}

export interface Store {
  id: number;
  name: string;
  slug: string;
  phone: string | null;
  address: string | null;
  created_at: string;
}

export interface DailyClosing {
  store_id: number;
  day: string;
  orders_created: number;
  delivered: number;
  cancelled: number;
  needs_review: number;
  amount_due_total: number;
  credit_extended_total: number;
}

export interface AuditEvent {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string;
  evidence: string | null;
  created_at: string;
}

export interface OutboundMessage {
  id: number;
  store_id: number;
  order_id: number | null;
  customer_id: number;
  destination_phone: string;
  body: string;
  provider: string;
  provider_message_id: string | null;
  failure_reason: string | null;
  dispatch_attempts: number;
  status: "queued" | "sent" | "simulated" | "failed";
  created_at: string;
  sent_at: string | null;
}

export interface DeliveryAgent {
  id: number;
  name: string;
  phone: string;
  active: boolean;
  created_at: string;
}

export interface DeliveryAssignment {
  id: number;
  order_id: number;
  agent_id: number;
  route_order: number;
  status: DeliveryStatus;
  notes: string | null;
  assigned_at: string;
  updated_at: string;
}

export interface RouteStop {
  assignment_id: number;
  order_id: number;
  customer_name: string;
  phone: string;
  building: string | null;
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  route_order: number;
  status: DeliveryStatus;
}

export interface RouteOptimizeResult {
  store_id: number;
  agent_id: number | null;
  ordered_order_ids: number[];
  stops: RouteStop[];
  strategy: string;
}

export interface Payment {
  id: number;
  customer_id: number | null;
  order_id: number | null;
  provider_ref: string;
  amount: number;
  payer_vpa: string | null;
  status: "received" | "reconciled" | "duplicate" | "failed";
  received_at: string;
  reconciled_at: string | null;
}

export interface Product {
  id: number;
  store_id: number;
  sku: string;
  name: string;
  canonical_name: string;
  category: string | null;
  unit: string;
  price: number | null;
  stock_quantity: number | null;
  status: "active" | "inactive";
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface StaffAssignment {
  id: number;
  store_id: number;
  order_id: number;
  operator_id: number;
  role: string;
  status: "assigned" | "accepted" | "completed" | "reassigned" | "cancelled";
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface OperationsDailyReport {
  store_id: number;
  day: string;
  orders_created: number;
  orders_delivered: number;
  orders_cancelled: number;
  needs_review: number;
  pending: number;
  packed: number;
  amount_due_total: number;
  credit_extended_total: number;
  average_order_value: number;
  manual_intervention_rate: number;
  top_items: TopItem[];
  ai_usage_count: number;
  ai_estimated_cost: number;
}

export interface FeatureFlags {
  catalog_enabled: boolean;
  staff_assignment_enabled: boolean;
  repeat_orders_enabled: boolean;
  ai_usage_tracking_enabled: boolean;
  payments_enabled: boolean;
  delivery_enabled: boolean;
}

export interface AiUsageSummary {
  store_id: number;
  day: string | null;
  total_events: number;
  total_estimated_units: number;
  total_estimated_cost: number;
  by_provider: Record<string, number>;
  by_purpose: Record<string, number>;
}

// ── HTTP helper ────────────────────────────────────────────────────────────────

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── API surface ────────────────────────────────────────────────────────────────

export const api = {
  // Auth
  login: async (username: string, password: string, store_id = 1) => {
    const token = await req<Token>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password, store_id }) });
    setAuthToken(token.access_token);
    return token;
  },
  logout: () => setAuthToken(null),
  currentStore: () => req<Store>("/api/stores/current"),
  features: () => req<FeatureFlags>("/api/features"),
  createOperator: (data: { username: string; password: string; role?: Operator["role"]; store_id?: number }) =>
    req<Operator>("/api/operators", { method: "POST", body: JSON.stringify(data) }),

  // Dashboard
  summary: () =>
    req<DashboardSummary>("/api/dashboard/summary"),
  dailyClosing: () => req<DailyClosing>("/api/dashboard/daily-closing"),

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
  correctItems: (id: number, items: Array<{ name: string; quantity: number; unit: string; confidence?: number }>, notes?: string) =>
    req<Order>(`/api/orders/${id}/items`, { method: "PATCH", body: JSON.stringify({ items, notes }) }),
  resolveReview: (id: number, items: Array<{ name: string; quantity: number; unit: string; confidence?: number }>, notes?: string) =>
    req<Order>(`/api/orders/${id}/review/resolve`, { method: "POST", body: JSON.stringify({ items, notes, status: "pending" }) }),
  confirmOrder: (id: number, body?: string) =>
    req<OutboundMessage>(`/api/orders/${id}/confirmations`, { method: "POST", body: JSON.stringify({ body }) }),
  updateOrderNotes: (id: number, notes: string | null) =>
    req<Order>(`/api/orders/${id}/notes`, { method: "PATCH", body: JSON.stringify({ notes }) }),
  repeatOrder: (id: number, notes?: string) =>
    req<Order>(`/api/orders/${id}/repeat`, { method: "POST", body: JSON.stringify({ notes }) }),
  assignStaff: (order_id: number, operator_id: number, role = "fulfillment", notes?: string) =>
    req<StaffAssignment>(`/api/orders/${order_id}/staff-assignments`, { method: "POST", body: JSON.stringify({ operator_id, role, notes }) }),
  staffAssignments: (params?: { order_id?: number; operator_id?: number }) => {
    const qs = new URLSearchParams();
    if (params?.order_id) qs.set("order_id", String(params.order_id));
    if (params?.operator_id) qs.set("operator_id", String(params.operator_id));
    return req<StaffAssignment[]>(`/api/staff-assignments?${qs}`);
  },

  // Customers
  customers: (dormant_only = false) =>
    req<Customer[]>(`/api/customers?dormant_only=${dormant_only}`),
  createCustomer: (data: { name: string; phone: string; building?: string }) =>
    req<Customer>("/api/customers", { method: "POST", body: JSON.stringify(data) }),
  updateCustomer: (id: number, data: Partial<Pick<Customer, "name" | "building" | "address" | "language_hint">>) =>
    req<Customer>(`/api/customers/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  adjustCredit: (customer_id: number, amount: number, reason: string) =>
    req<Customer>(`/api/customers/${customer_id}/credit`, {
      method: "POST",
      body: JSON.stringify({ amount, reason }),
    }),
  ledger: (customer_id: number) =>
    req<LedgerEntry[]>(`/api/customers/${customer_id}/ledger`),
  customerHistory: (customer_id: number) =>
    req<{ customer: Customer; recent_orders: Order[]; lifetime_orders: number; lifetime_amount_due: number; top_items: TopItem[] }>(`/api/customers/${customer_id}/history`),

  // Catalog
  products: (q?: string) => {
    const qs = new URLSearchParams();
    if (q) qs.set("q", q);
    return req<Product[]>(`/api/catalog/products?${qs}`);
  },
  createProduct: (data: Partial<Product> & { sku: string; name: string }) =>
    req<Product>("/api/catalog/products", { method: "POST", body: JSON.stringify(data) }),
  updateProduct: (id: number, data: Partial<Product>) =>
    req<Product>(`/api/catalog/products/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  // Delivery
  createDeliveryAgent: (data: { name: string; phone: string; active?: boolean }) =>
    req<DeliveryAgent>("/api/delivery/agents", { method: "POST", body: JSON.stringify(data) }),
  deliveryAgents: () =>
    req<DeliveryAgent[]>("/api/delivery/agents"),
  assignDelivery: (order_id: number, agent_id: number, route_order = 0, notes?: string) =>
    req<DeliveryAssignment>(`/api/orders/${order_id}/delivery`, {
      method: "POST",
      body: JSON.stringify({ agent_id, route_order, notes }),
    }),
  deliveryRoute: (agent_id: number) =>
    req<RouteStop[]>(`/api/delivery/agents/${agent_id}/route`),
  optimizeRoute: (data: {
    agent_id?: number; order_ids?: number[];
    start_latitude?: number; start_longitude?: number;
  }) => req<RouteOptimizeResult>("/api/delivery/routes/optimize", {
    method: "POST",
    body: JSON.stringify(data),
  }),

  // Payments
  reconcileUpi: (data: {
    provider_ref: string; amount: number; payer_vpa?: string;
    customer_id?: number; order_id?: number; raw_payload?: Record<string, unknown>;
  }) => req<Payment>("/api/payments/upi/webhook", { method: "POST", body: JSON.stringify(data) }),

  // Ingest (demo / manual)
  ingest: (payload: {
    phone: string; customer_name?: string; building?: string;
    message_type?: MessageType; text?: string;
  }) => req<Order>("/api/ingest/messages", { method: "POST", body: JSON.stringify(payload) }),

  // Operations
  operationsDailyReport: () => req<OperationsDailyReport>("/api/operations/daily-report"),
  aiUsageSummary: () => req<AiUsageSummary>("/api/operations/ai-usage/summary"),

  // Analytics
  daily: (days = 7) =>
    req<DailyMetric[]>(`/api/analytics/daily?days=${days}`),
  topItems: (days = 30, limit = 10) =>
    req<TopItem[]>(`/api/analytics/top-items?days=${days}&limit=${limit}`),
  inputMethods: (days = 30) =>
    req<InputMethodStat[]>(`/api/analytics/input-methods?days=${days}`),
  auditEvents: (entity_type?: string, entity_id?: number | string) => {
    const qs = new URLSearchParams();
    if (entity_type) qs.set("entity_type", entity_type);
    if (entity_id) qs.set("entity_id", String(entity_id));
    return req<AuditEvent[]>(`/api/audit/events?${qs}`);
  },
};
