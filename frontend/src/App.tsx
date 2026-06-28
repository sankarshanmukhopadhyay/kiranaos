/**
 * App.tsx — KiranaOS dashboard.
 *
 * Four views: Dashboard (inbox + orders), Customers, Udhaari, Analytics.
 * All data fetches from the real backend API. Falls back gracefully when
 * the backend is unreachable (shows last loaded data + error banner).
 *
 * Design tokens: ink navy sidebar, warm paper main panel, saffron accent,
 * Space Grotesk headings, Inter body — same visual identity as KiranaOS v1.
 */

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import "./styles.css";
import { SIDEBAR_ICONS, SIDEBAR_LABELS } from "./sidebarMeta";

import {
  api,
  Customer,
  DailyMetric,
  DashboardSummary,
  InputMethodStat,
  Order,
  OrderStatus,
  TopItem,
} from "./lib/api";

// ── State ─────────────────────────────────────────────────────────────────────

interface AppState {
  view:        "dashboard" | "customers" | "udhaari" | "analytics";
  summary:     DashboardSummary;
  orders:      Order[];
  customers:   Customer[];
  daily:       DailyMetric[];
  topItems:    TopItem[];
  inputStats:  InputMethodStat[];
  loading:     boolean;
  error:       string | null;
  filter:      OrderStatus | "all";
  search:      string;
}

const EMPTY_SUMMARY: DashboardSummary = {
  pending: 0, packed: 0, delivered_today: 0,
  needs_review: 0, dormant_customers: 0, total_credit: 0,
};

const initial: AppState = {
  view: "dashboard", summary: EMPTY_SUMMARY,
  orders: [], customers: [], daily: [], topItems: [], inputStats: [],
  loading: true, error: null, filter: "all", search: "",
};

type Action =
  | { type: "SET_VIEW"; view: AppState["view"] }
  | { type: "LOADED"; data: Partial<AppState> }
  | { type: "ERROR"; msg: string }
  | { type: "SET_FILTER"; filter: AppState["filter"] }
  | { type: "SET_SEARCH"; search: string }
  | { type: "ORDER_UPDATED"; order: Order }
  | { type: "CUSTOMER_UPDATED"; customer: Customer };

function reducer(s: AppState, a: Action): AppState {
  switch (a.type) {
    case "SET_VIEW":    return { ...s, view: a.view, loading: true, error: null };
    case "LOADED":      return { ...s, ...a.data, loading: false, error: null };
    case "ERROR":       return { ...s, loading: false, error: a.msg };
    case "SET_FILTER":  return { ...s, filter: a.filter };
    case "SET_SEARCH":  return { ...s, search: a.search };
    case "ORDER_UPDATED":
      return { ...s, orders: s.orders.map(o => o.id === a.order.id ? a.order : o) };
    case "CUSTOMER_UPDATED":
      return { ...s, customers: s.customers.map(c => c.id === a.customer.id ? a.customer : c) };
    default: return s;
  }
}

// ── Toast ──────────────────────────────────────────────────────────────────────

function useToast() {
  const [msg, setMsg] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const show = useCallback((m: string) => {
    setMsg(m);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setMsg(null), 3000);
  }, []);
  return { msg, show };
}

// ── Main App ───────────────────────────────────────────────────────────────────

export default function App() {
  const [s, dispatch] = useReducer(reducer, initial);
  const toast = useToast();

  // ── Data loading ─────────────────────────────────────────────────────────────

  const loadDashboard = useCallback(async () => {
    try {
      const [summary, orders] = await Promise.all([api.summary(), api.orders()]);
      dispatch({ type: "LOADED", data: { summary, orders } });
    } catch (e) {
      dispatch({ type: "ERROR", msg: String(e) });
    }
  }, []);

  const loadCustomers = useCallback(async () => {
    try {
      const customers = await api.customers();
      dispatch({ type: "LOADED", data: { customers } });
    } catch (e) {
      dispatch({ type: "ERROR", msg: String(e) });
    }
  }, []);

  const loadAnalytics = useCallback(async () => {
    try {
      const [daily, topItems, inputStats] = await Promise.all([
        api.daily(7), api.topItems(30, 8), api.inputMethods(30),
      ]);
      dispatch({ type: "LOADED", data: { daily, topItems, inputStats } });
    } catch (e) {
      dispatch({ type: "ERROR", msg: String(e) });
    }
  }, []);

  useEffect(() => {
    if (s.view === "dashboard") loadDashboard();
    else if (s.view === "customers" || s.view === "udhaari") loadCustomers();
    else if (s.view === "analytics") loadAnalytics();
  }, [s.view, loadDashboard, loadCustomers, loadAnalytics]);

  // ── Actions ───────────────────────────────────────────────────────────────────

  const setStatus = async (id: number, status: OrderStatus) => {
    try {
      const updated = await api.setStatus(id, status);
      dispatch({ type: "ORDER_UPDATED", order: updated });
      toast.show(`Order #${id} → ${status}`);
      // Refresh summary counts
      const summary = await api.summary();
      dispatch({ type: "LOADED", data: { summary } });
    } catch (e) {
      toast.show(`Failed: ${e}`);
    }
  };

  const settleCredit = async (customerId: number, amount: number, name: string) => {
    try {
      const updated = await api.adjustCredit(customerId, -amount, "Cash payment");
      dispatch({ type: "CUSTOMER_UPDATED", customer: updated });
      toast.show(`₹${amount} recorded from ${name}`);
    } catch (e) {
      toast.show(`Failed: ${e}`);
    }
  };

  // ── Simulate inbound message (demo) ──────────────────────────────────────────

  const DEMO_MESSAGES = [
    { customer_name: "Farhan Ahmed", building: "Bldg C", text: "besan 1kg, namkeen 2 packet, bisleri 1L" },
    { customer_name: "Priya Demo",   building: "Bldg D", text: "sunflower oil 1L, maida 1kg, dahi 400g" },
    { customer_name: "Ravi Demo",    building: "Bldg A", text: "Maggi 6 packet, bread, butter" },
  ];
  const demoIdx = useRef(0);
  const simulateMessage = async () => {
    const msg = DEMO_MESSAGES[demoIdx.current % DEMO_MESSAGES.length];
    demoIdx.current++;
    const phone = `+9198${Math.floor(Math.random() * 90000000 + 10000000)}`;
    try {
      await api.ingest({ phone, ...msg });
      toast.show(`New order parsed from ${msg.customer_name}!`);
      await loadDashboard();
    } catch (e) {
      toast.show(`Ingest failed: ${e}`);
    }
  };

  // ── Derived data ──────────────────────────────────────────────────────────────

  const visibleOrders = s.orders.filter(o => {
    const matchFilter = s.filter === "all" || o.status === s.filter;
    const matchSearch = !s.search ||
      o.customer.name.toLowerCase().includes(s.search.toLowerCase()) ||
      o.items.some(i => i.name.toLowerCase().includes(s.search.toLowerCase()));
    return matchFilter && matchSearch;
  });

  const ghostCustomers = s.customers.filter(c => c.dormant);
  const udhaariCustomers = s.customers.filter(c => c.credit_balance > 0);

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <>

      {/* Nav */}
      <nav className="nav">
        <div className="nav-logo">
          <div className="nav-logo-dot" />
          Kirana<span>OS</span>
        </div>
        <div className="nav-meta">
          <span className="nav-store">Ramesh Kirana, Koramangala</span>
          <div className="nav-avatar">RK</div>
        </div>
      </nav>

      <div className="shell">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-section-label">Orders</div>
          {(["dashboard", "customers", "udhaari", "analytics"] as const).map(v => (
            <button
              key={v}
              className={`sidebar-item${s.view === v ? " active" : ""}`}
              onClick={() => dispatch({ type: "SET_VIEW", view: v })}
            >
              {SIDEBAR_ICONS[v]}
              {SIDEBAR_LABELS[v]}
              {v === "dashboard" && s.summary.pending > 0 &&
                <span className="sidebar-badge">{s.summary.pending}</span>}
              {v === "customers" && ghostCustomers.length > 0 &&
                <span className="sidebar-badge red">{ghostCustomers.length}</span>}
            </button>
          ))}

          <hr className="sidebar-divider" />
          <div className="sidebar-section-label">Demo</div>
          <button className="sidebar-item" onClick={simulateMessage}>
            {SIDEBAR_ICONS.simulate}
            Simulate WA Message
          </button>

          <div className="sidebar-stats">
            <div className="stat-row">
              <span className="stat-label">Today's Revenue</span>
              <span className="stat-value saffron">
                ₹{(s.summary.delivered_today * 450).toLocaleString("en-IN")}
              </span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Delivered Today</span>
              <span className="stat-value green">{s.summary.delivered_today}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Udhaari Owed</span>
              <span className="stat-value" style={{ color: "var(--red)" }}>
                ₹{s.summary.total_credit.toLocaleString("en-IN")}
              </span>
            </div>
          </div>
        </aside>

        {/* Main */}
        <main className="main">
          {s.error && (
            <div className="error-banner">
              ⚠ {s.error} — Is the backend running? (<code>make dev</code>)
            </div>
          )}

          {/* ── Dashboard ─────────────────────────────────────────────────── */}
          {s.view === "dashboard" && (
            <div className="view-inner">
              <div className="dashboard-header">
                <div>
                  <div className="dashboard-title">Order Dashboard</div>
                  <div className="dashboard-subtitle">
                    {new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}
                  </div>
                </div>
                <button className="btn btn-saffron" onClick={simulateMessage}>+ Simulate Order</button>
              </div>

              {/* Stats strip */}
              <div className="stats-strip">
                {[
                  { label: "Pending",      value: s.summary.pending,          color: "saffron" },
                  { label: "Packing",      value: s.summary.packed,           color: "blue" },
                  { label: "Delivered",    value: s.summary.delivered_today,  color: "green" },
                  { label: "Needs Review", value: s.summary.needs_review,     color: "red" },
                  { label: "Dormant",      value: s.summary.dormant_customers, color: "red" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="stat-card">
                    <div className="stat-card-label">{label}</div>
                    <div className={`stat-card-value ${color}`}>{value}</div>
                  </div>
                ))}
              </div>

              {/* Dual panel */}
              <div className="dual-panel">
                {/* WA Inbox panel */}
                <div className="inbox-panel">
                  <div className="inbox-header">
                    <div className="whatsapp-dot" />
                    <div>
                      <div className="inbox-header-title">WhatsApp Orders</div>
                      <div className="inbox-header-sub">Live · auto-parsed</div>
                    </div>
                  </div>
                  <div className="inbox-feed">
                    {s.orders.slice(0, 12).map(o => (
                      <div key={o.id} className={`wa-bubble${o.status === "needs_review" ? " review" : " parsed"}`}>
                        <div className="wa-sender">{o.customer.name} ({o.customer.phone})</div>
                        <div className="wa-text">
                          {o.items.length > 0
                            ? o.items.map(i => `${i.name} ${i.quantity}${i.unit}`).join(", ")
                            : o.notes ?? "Media message"}
                        </div>
                        <div className="wa-meta">
                          <span className="wa-time">
                            {new Date(o.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                          </span>
                          <span className={`wa-badge ${o.status === "needs_review" ? "parsing" : "parsed"}`}>
                            {o.status === "needs_review" ? "⚠ Review" : "✓ Parsed"}
                          </span>
                        </div>
                      </div>
                    ))}
                    {s.orders.length === 0 && !s.loading && (
                      <div className="empty-feed">No messages yet. Click "Simulate WA Message" to begin.</div>
                    )}
                  </div>
                </div>

                {/* Orders panel */}
                <div className="orders-panel">
                  <div className="orders-toolbar">
                    <div className="filter-tabs">
                      {(["all", "pending", "packed", "delivered", "needs_review"] as const).map(f => (
                        <button
                          key={f}
                          className={`filter-tab${s.filter === f ? " active" : ""}`}
                          onClick={() => dispatch({ type: "SET_FILTER", filter: f })}
                        >
                          {f.replace("_", " ")}
                        </button>
                      ))}
                    </div>
                    <input
                      className="search-input"
                      placeholder="Search customer or item…"
                      value={s.search}
                      onChange={e => dispatch({ type: "SET_SEARCH", search: e.target.value })}
                    />
                  </div>
                  <div className="orders-list">
                    {ghostCustomers.length > 0 && s.filter === "all" && (
                      <div className="churn-banner">
                        <span>👻</span>
                        <span><strong>{ghostCustomers.length} customers</strong> silent for 14+ days</span>
                        <button onClick={() => dispatch({ type: "SET_VIEW", view: "customers" })}>
                          View →
                        </button>
                      </div>
                    )}
                    {visibleOrders.map(o => (
                      <OrderCard key={o.id} order={o} onStatus={setStatus} />
                    ))}
                    {visibleOrders.length === 0 && !s.loading && (
                      <div className="empty-orders">No orders in this lane.</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── Customers ─────────────────────────────────────────────────── */}
          {s.view === "customers" && (
            <div className="view-inner">
              <div className="dashboard-header">
                <div>
                  <div className="dashboard-title">Customers</div>
                  <div className="dashboard-subtitle">{s.customers.length} families · {ghostCustomers.length} at churn risk</div>
                </div>
              </div>
              {ghostCustomers.length > 0 && (
                <div className="churn-banner" style={{ margin: "16px 24px 0" }}>
                  <span>👻</span>
                  <span><strong>{ghostCustomers.length} customers</strong> haven't ordered in 14+ days. They may be using Blinkit or Zepto.</span>
                </div>
              )}
              <div className="table-wrapper">
                <table className="customer-table">
                  <thead>
                    <tr>
                      <th>Customer</th><th>Building</th><th>Last Order</th>
                      <th>Udhaari</th><th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {s.customers.map(c => {
                      const daysSince = c.last_order_at
                        ? Math.floor((Date.now() - new Date(c.last_order_at).getTime()) / 86400000)
                        : null;
                      const recencyClass = daysSince === null ? "danger"
                        : daysSince === 0 ? "ok"
                        : daysSince <= 7 ? "warn" : "danger";
                      return (
                        <tr key={c.id}>
                          <td>
                            <div className="customer-name">{c.name}</div>
                            <div className="customer-phone">{c.phone}</div>
                          </td>
                          <td>{c.building ?? "—"}</td>
                          <td className={`recency-${recencyClass}`}>
                            {daysSince === null ? "Never" : daysSince === 0 ? "Today" : `${daysSince}d ago`}
                          </td>
                          <td className={c.credit_balance > 0 ? "credit-owed" : ""}>
                            {c.credit_balance > 0 ? `₹${c.credit_balance.toFixed(0)}` : "—"}
                          </td>
                          <td>
                            {c.dormant
                              ? <span className="ghost-tag">👻 At Risk</span>
                              : <span className="active-tag">● Active</span>}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── Udhaari ───────────────────────────────────────────────────── */}
          {s.view === "udhaari" && (
            <div className="view-inner">
              <div className="dashboard-header">
                <div>
                  <div className="dashboard-title">Udhaari Ledger</div>
                  <div className="dashboard-subtitle">Always tracked · never lost in a diary</div>
                </div>
              </div>
              <div className="udhaari-content">
                <div className="udhaari-summary-grid">
                  <div className="udhaari-sum-card">
                    <div className="udhaari-sum-label">Total Outstanding</div>
                    <div className="udhaari-sum-value red">₹{s.summary.total_credit.toFixed(0)}</div>
                  </div>
                  <div className="udhaari-sum-card">
                    <div className="udhaari-sum-label">Customers with Balance</div>
                    <div className="udhaari-sum-value">{udhaariCustomers.length}</div>
                  </div>
                  <div className="udhaari-sum-card">
                    <div className="udhaari-sum-label">Avg. per Customer</div>
                    <div className="udhaari-sum-value">
                      ₹{udhaariCustomers.length
                        ? (s.summary.total_credit / udhaariCustomers.length).toFixed(0)
                        : 0}
                    </div>
                  </div>
                </div>
                <div className="udhaari-list">
                  {udhaariCustomers.length === 0 && (
                    <div className="empty-orders" style={{ padding: 32 }}>No outstanding udhaari balances.</div>
                  )}
                  {udhaariCustomers.map(c => (
                    <div key={c.id} className={`udhaari-row${c.credit_balance > 500 ? " overdue" : ""}`}>
                      <div className="udhaari-avatar">{c.name[0]}</div>
                      <div className="udhaari-info">
                        <div className="udhaari-name">{c.name}</div>
                        <div className="udhaari-building">{c.building ?? c.phone}</div>
                      </div>
                      <div className="udhaari-amount">₹{c.credit_balance.toFixed(0)}</div>
                      <button
                        className="settle-btn"
                        onClick={() => settleCredit(c.id, c.credit_balance, c.name)}
                      >
                        Mark Paid
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Analytics ─────────────────────────────────────────────────── */}
          {s.view === "analytics" && (
            <div className="view-inner">
              <div className="dashboard-header">
                <div>
                  <div className="dashboard-title">Analytics</div>
                  <div className="dashboard-subtitle">Last 7 days · generated from real order data</div>
                </div>
              </div>
              <div className="analytics-content">
                <div className="analytics-grid">
                  <BarChart
                    title="Daily Orders"
                    data={s.daily.map(d => ({ label: d.day.slice(5), value: d.orders }))}
                    color="var(--ink)"
                  />
                  <BarChart
                    title="Daily Revenue ₹"
                    data={s.daily.map(d => ({ label: d.day.slice(5), value: d.revenue }))}
                    color="var(--saffron)"
                    format={v => `₹${(v / 1000).toFixed(1)}k`}
                  />
                </div>
                <div className="analytics-grid">
                  <RankList
                    title="Top Items (30 days)"
                    items={s.topItems.map(i => ({ name: i.name, value: i.count, sub: `${i.total_quantity} units` }))}
                    color="var(--saffron)"
                  />
                  <RankList
                    title="Order Input Method"
                    items={s.inputStats.map(i => ({ name: i.message_type, value: i.count }))}
                    color="var(--ink)"
                  />
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Toast */}
      {toast.msg && <div className="toast">{toast.msg}</div>}
    </>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function OrderCard({ order, onStatus }: { order: Order; onStatus: (id: number, s: OrderStatus) => void }) {
  const time = new Date(order.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  const hasLowConfidence = order.items.some(i => i.confidence < 0.7);

  return (
    <div className={`order-card${order.status === "needs_review" ? " flagged" : ""}`}>
      <div className="order-card-header">
        <div>
          <div className="order-customer">{order.customer.name}</div>
          <div className="order-building">{order.customer.building ?? "Building unknown"} · {time}</div>
        </div>
        <span className={`status-pill ${order.status}`}>{order.status.replace("_", " ")}</span>
      </div>

      <div className="order-items">
        {order.items.slice(0, 4).map(item => (
          <span
            key={item.id}
            className={`item-tag${item.confidence < 0.7 ? " low-confidence" : ""}`}
            title={item.confidence < 0.7 ? `Low confidence (${(item.confidence * 100).toFixed(0)}%)` : undefined}
          >
            {item.name} {item.quantity !== 1 ? `${item.quantity}${item.unit}` : ""}
          </span>
        ))}
        {order.items.length > 4 && <span className="item-tag more">+{order.items.length - 4} more</span>}
        {order.items.length === 0 && order.notes && (
          <span className="item-tag needs-review-tag">{order.notes}</span>
        )}
      </div>

      {hasLowConfidence && (
        <div className="low-confidence-note">⚠ Some items parsed with low confidence — verify before packing</div>
      )}

      <div className="order-footer">
        {order.is_credit && <span className="udhaari-badge">Udhaari</span>}
        {order.amount_due > 0 && <span className="order-amount">₹{order.amount_due.toFixed(0)}</span>}
        <div className="order-actions">
          {order.status === "pending"      && <button className="order-btn primary" onClick={() => onStatus(order.id, "packed")}>Pack</button>}
          {order.status === "packed"       && <button className="order-btn green"   onClick={() => onStatus(order.id, "delivered")}>Deliver</button>}
          {order.status === "needs_review" && <button className="order-btn primary" onClick={() => onStatus(order.id, "pending")}>Mark Pending</button>}
          {order.status === "delivered"    && <span className="delivered-label">✓ Done</span>}
        </div>
      </div>
    </div>
  );
}

function BarChart({
  title, data, color, format,
}: {
  title: string;
  data: { label: string; value: number }[];
  color: string;
  format?: (v: number) => string;
}) {
  const max = Math.max(...data.map(d => d.value), 1);
  return (
    <div className="chart-card">
      <div className="chart-title">{title}</div>
      <div className="bar-chart">
        {data.map(d => (
          <div key={d.label} className="bar-group">
            <div className="bar-val">{format ? format(d.value) : d.value}</div>
            <div className="bar" style={{ height: `${(d.value / max) * 80}px`, background: color }} />
            <div className="bar-label">{d.label}</div>
          </div>
        ))}
        {data.length === 0 && <div className="empty-orders">No data yet.</div>}
      </div>
    </div>
  );
}

function RankList({
  title, items, color,
}: {
  title: string;
  items: { name: string; value: number; sub?: string }[];
  color: string;
}) {
  const max = Math.max(...items.map(i => i.value), 1);
  return (
    <div className="chart-card">
      <div className="chart-title">{title}</div>
      <div className="rank-list">
        {items.map((item, idx) => (
          <div key={item.name} className="rank-row">
            <span className="rank-num">{idx + 1}</span>
            <span className="rank-name">{item.name}{item.sub ? ` (${item.sub})` : ""}</span>
            <div className="rank-bar-wrap">
              <div className="rank-bar" style={{ width: `${(item.value / max) * 100}%`, background: color }} />
            </div>
            <span className="rank-val">{item.value}</span>
          </div>
        ))}
        {items.length === 0 && <div className="empty-orders">No data yet.</div>}
      </div>
    </div>
  );
}
