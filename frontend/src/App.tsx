import { useCallback, useEffect, useMemo, useState } from "react";
import "./styles.css";
import { api, AuditEvent, Customer, DailyClosing, DashboardSummary, getAuthToken, Order, OrderStatus, Settlement, Store } from "./lib/api";

type View = "dashboard" | "review" | "customers" | "closing" | "finance";

const EMPTY_SUMMARY: DashboardSummary = {
  pending: 0,
  packed: 0,
  delivered_today: 0,
  needs_review: 0,
  dormant_customers: 0,
  total_credit: 0,
};

const STATUS_FLOW: Record<OrderStatus, OrderStatus[]> = {
  needs_review: ["pending", "cancelled"],
  pending: ["packed", "cancelled"],
  packed: ["delivered", "cancelled"],
  delivered: [],
  cancelled: [],
};

function App() {
  const [view, setView] = useState<View>("dashboard");
  const [summary, setSummary] = useState<DashboardSummary>(EMPTY_SUMMARY);
  const [orders, setOrders] = useState<Order[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [store, setStore] = useState<Store | null>(null);
  const [closing, setClosing] = useState<DailyClosing | null>(null);
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [selected, setSelected] = useState<Order | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [filter, setFilter] = useState<OrderStatus | "all">("all");
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [tokenPresent, setTokenPresent] = useState(Boolean(getAuthToken()));
  const [login, setLogin] = useState({ username: "", password: "", store_id: 1 });

  const showToast = (msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 2600);
  };

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const [nextSummary, nextOrders, nextCustomers, nextStore, nextClosing] = await Promise.all([
        api.summary(),
        api.orders(),
        api.customers(),
        api.currentStore(),
        api.dailyClosing(),
      ]);
      setSummary(nextSummary);
      setOrders(nextOrders);
      setCustomers(nextCustomers);
      setStore(nextStore);
      setClosing(nextClosing);
      try { setSettlements(await api.settlements()); } catch { setSettlements([]); }
    } catch (err) {
      setError(String(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const visibleOrders = useMemo(
    () => orders.filter((order) => filter === "all" || order.status === filter),
    [orders, filter],
  );

  const reviewOrders = useMemo(
    () => orders.filter((order) => order.status === "needs_review"),
    [orders],
  );

  async function handleLogin() {
    try {
      await api.login(login.username, login.password, login.store_id);
      setTokenPresent(true);
      showToast("Signed in");
      await refresh();
    } catch (err) {
      showToast(`Login failed: ${err}`);
    }
  }

  async function handleLogout() {
    api.logout();
    setTokenPresent(false);
    showToast("Signed out");
  }

  async function loadAudit(order: Order) {
    setSelected(order);
    try {
      setAudit(await api.auditEvents("order", order.id));
    } catch {
      setAudit([]);
    }
  }

  async function setStatus(order: Order, status: OrderStatus) {
    try {
      const updated = await api.setStatus(order.id, status);
      setOrders((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      if (selected?.id === updated.id) setSelected(updated);
      showToast(`Order #${order.id} moved to ${status.replace("_", " ")}`);
      await refresh();
    } catch (err) {
      showToast(`Status update failed: ${err}`);
    }
  }

  async function resolveReview(order: Order) {
    const items = order.items.length
      ? order.items.map((item) => ({ name: item.name, quantity: item.quantity, unit: item.unit, confidence: 1 }))
      : [{ name: "Manual item", quantity: 1, unit: "pcs", confidence: 1 }];
    try {
      const updated = await api.resolveReview(order.id, items, "Reviewed by operator");
      setOrders((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSelected(updated);
      showToast(`Order #${order.id} resolved`);
      await refresh();
    } catch (err) {
      showToast(`Review resolution failed: ${err}`);
    }
  }

  async function simulateOrder() {
    const sample = { phone: `+9198${Math.floor(Math.random() * 90000000 + 10000000)}`, customer_name: "Pilot Customer", building: "Demo Block", text: "2 kg atta, 1 l oil, bread" };
    try {
      await api.ingest(sample);
      showToast("Demo order ingested");
      await refresh();
    } catch (err) {
      showToast(`Ingest failed: ${err}`);
    }
  }

  return (
    <>
      <nav className="nav">
        <div className="nav-logo"><div className="nav-logo-dot" />Kirana<span>OS</span></div>
        <div className="nav-meta">
          <span className="nav-store">{store ? `${store.name} · ${store.slug}` : "Pilot workspace"}</span>
          {tokenPresent ? <button className="order-btn" onClick={handleLogout}>Logout</button> : <span className="nav-store">Demo mode</span>}
          <div className="nav-avatar">KO</div>
        </div>
      </nav>

      <div className="shell">
        <aside className="sidebar">
          <div className="sidebar-section-label">Pilot workflow</div>
          {([
            ["dashboard", "Orders"],
            ["review", `Review Queue (${summary.needs_review})`],
            ["customers", "Customers"],
            ["closing", "Daily Closing"],
            ["finance", "Order-to-Cash"],
          ] as const).map(([key, label]) => (
            <button key={key} className={`sidebar-item${view === key ? " active" : ""}`} onClick={() => setView(key)}>
              <span>•</span>{label}
            </button>
          ))}
          <hr className="sidebar-divider" />
          <div className="sidebar-section-label">Operator</div>
          {!tokenPresent && (
            <div className="login-box">
              <input placeholder="username" value={login.username} onChange={(e) => setLogin({ ...login, username: e.target.value })} />
              <input placeholder="password" type="password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} />
              <button className="btn btn-saffron" onClick={handleLogin}>Login</button>
            </div>
          )}
          <button className="sidebar-item" onClick={simulateOrder}>+ Simulate WA order</button>
        </aside>

        <main className="main">
          {error && <div className="error-banner">{error}</div>}

          {view === "dashboard" && (
            <section className="view-inner">
              <Header title="Order Dashboard" subtitle="Pilot-safe order lifecycle with review-first controls" action={<button className="btn btn-saffron" onClick={simulateOrder}>+ Simulate Order</button>} />
              <Stats summary={summary} />
              <div className="orders-toolbar">
                {(["all", "needs_review", "pending", "packed", "delivered", "cancelled"] as const).map((item) => (
                  <button key={item} className={`filter-tab${filter === item ? " active" : ""}`} onClick={() => setFilter(item)}>{item.replace("_", " ")}</button>
                ))}
              </div>
              <div className="orders-list">
                {visibleOrders.map((order) => <OrderCard key={order.id} order={order} onOpen={loadAudit} onStatus={setStatus} onResolve={resolveReview} />)}
                {visibleOrders.length === 0 && <div className="empty-orders">No orders in this lane.</div>}
              </div>
            </section>
          )}

          {view === "review" && (
            <section className="view-inner">
              <Header title="Review Queue" subtitle="Low-confidence and unparsed messages require operator confirmation before fulfillment" />
              <div className="orders-list">
                {reviewOrders.map((order) => <OrderCard key={order.id} order={order} onOpen={loadAudit} onStatus={setStatus} onResolve={resolveReview} />)}
                {reviewOrders.length === 0 && <div className="empty-orders">No orders currently need review.</div>}
              </div>
            </section>
          )}

          {view === "customers" && (
            <section className="view-inner">
              <Header title="Customers" subtitle={`${customers.length} customer records · ${summary.dormant_customers} dormant`} />
              <div className="table-wrapper">
                <table className="customer-table">
                  <thead><tr><th>Customer</th><th>Building</th><th>Language</th><th>Udhaari</th><th>Last Order</th></tr></thead>
                  <tbody>{customers.map((customer) => (
                    <tr key={customer.id}>
                      <td><div className="customer-name">{customer.name}</div><div className="customer-phone">{customer.phone}</div></td>
                      <td>{customer.building ?? "—"}</td>
                      <td>{customer.language_hint ?? "—"}</td>
                      <td className={customer.credit_balance > 0 ? "credit-owed" : ""}>₹{customer.credit_balance.toFixed(0)}</td>
                      <td>{customer.last_order_at ? new Date(customer.last_order_at).toLocaleDateString("en-IN") : "Never"}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </section>
          )}

          {view === "finance" && (
            <section className="view-inner">
              <Header title="Order-to-Cash" subtitle="Tender reconciliation, settlement closure, and accounting handoff" action={<button className="btn btn-saffron" onClick={async () => { try { await api.generateSettlement(); showToast("Settlement generated"); await refresh(); } catch (err) { showToast(`Settlement failed: ${err}`); } }}>Generate settlement</button>} />
              <div className="udhaari-summary-grid">
                <ClosingCard label="Cash" value={`₹${(settlements[0]?.cash_total ?? 0).toFixed(0)}`} />
                <ClosingCard label="UPI" value={`₹${(settlements[0]?.upi_total ?? 0).toFixed(0)}`} />
                <ClosingCard label="Refunds" value={`₹${(settlements[0]?.refund_total ?? 0).toFixed(0)}`} />
                <ClosingCard label="Net Receipts" value={`₹${(settlements[0]?.net_total ?? 0).toFixed(0)}`} />
              </div>
              <div className="orders-toolbar">
                <a className="btn btn-saffron" href="/api/accounting/export?format=csv">Export CSV</a>
                <a className="btn" href="/api/accounting/export?format=xlsx">Export XLSX</a>
              </div>
              <div className="table-wrapper">
                <table className="customer-table"><thead><tr><th>Day</th><th>Payments</th><th>Cash</th><th>UPI</th><th>Refunds</th><th>Net</th><th>Status</th></tr></thead>
                <tbody>{settlements.map((row) => <tr key={row.id}><td>{row.business_day}</td><td>{row.payment_count}</td><td>₹{row.cash_total.toFixed(0)}</td><td>₹{row.upi_total.toFixed(0)}</td><td>₹{row.refund_total.toFixed(0)}</td><td>₹{row.net_total.toFixed(0)}</td><td>{row.status}</td></tr>)}</tbody></table>
              </div>
            </section>
          )}

          {view === "closing" && (
            <section className="view-inner">
              <Header title="Daily Closing" subtitle="Basic pilot summary for order and credit reconciliation" />
              <div className="udhaari-summary-grid">
                <ClosingCard label="Orders Created" value={closing?.orders_created ?? 0} />
                <ClosingCard label="Delivered" value={closing?.delivered ?? 0} />
                <ClosingCard label="Needs Review" value={closing?.needs_review ?? 0} />
                <ClosingCard label="Amount Due" value={`₹${(closing?.amount_due_total ?? 0).toFixed(0)}`} />
                <ClosingCard label="Credit Extended" value={`₹${(closing?.credit_extended_total ?? 0).toFixed(0)}`} />
              </div>
            </section>
          )}

          {selected && <OrderDrawer order={selected} audit={audit} onClose={() => setSelected(null)} />}
        </main>
      </div>
      {toast && <div className="toast">{toast}</div>}
    </>
  );
}

function Header({ title, subtitle, action }: { title: string; subtitle: string; action?: JSX.Element }) {
  return <div className="dashboard-header"><div><div className="dashboard-title">{title}</div><div className="dashboard-subtitle">{subtitle}</div></div>{action}</div>;
}

function Stats({ summary }: { summary: DashboardSummary }) {
  const items = [
    ["Pending", summary.pending, "saffron"],
    ["Packed", summary.packed, "blue"],
    ["Delivered Today", summary.delivered_today, "green"],
    ["Needs Review", summary.needs_review, "red"],
    ["Udhaari", `₹${summary.total_credit.toFixed(0)}`, "red"],
  ] as const;
  return <div className="stats-strip">{items.map(([label, value, color]) => <div className="stat-card" key={label}><div className="stat-card-label">{label}</div><div className={`stat-card-value ${color}`}>{value}</div></div>)}</div>;
}

function OrderCard({ order, onOpen, onStatus, onResolve }: { order: Order; onOpen: (order: Order) => void; onStatus: (order: Order, status: OrderStatus) => void; onResolve: (order: Order) => void }) {
  const transitions = STATUS_FLOW[order.status];
  return (
    <div className={`order-card${order.status === "needs_review" ? " flagged" : ""}`}>
      <div className="order-card-header">
        <div><div className="order-customer">#{order.id} · {order.customer.name}</div><div className="order-building">{order.customer.phone} · {order.customer.building ?? "Building unknown"}</div></div>
        <span className={`status-pill ${order.status}`}>{order.status.replace("_", " ")}</span>
      </div>
      <div className="order-items">
        {order.items.map((item) => <span className={`item-tag${item.confidence < 0.7 ? " low-confidence" : ""}`} key={item.id}>{item.name} {item.quantity}{item.unit}</span>)}
        {order.items.length === 0 && <span className="item-tag needs-review-tag">{order.notes ?? "Review raw message"}</span>}
      </div>
      {order.message?.parse_failure_reason && <div className="low-confidence-note">Reason: {order.message.parse_failure_reason}</div>}
      <div className="order-footer">
        <button className="order-btn" onClick={() => onOpen(order)}>Inspect</button>
        {order.status === "needs_review" && <button className="order-btn primary" onClick={() => onResolve(order)}>Resolve Review</button>}
        {transitions.map((status) => <button className="order-btn" key={status} onClick={() => onStatus(order, status)}>{status.replace("_", " ")}</button>)}
      </div>
    </div>
  );
}

function ClosingCard({ label, value }: { label: string; value: string | number }) {
  return <div className="udhaari-sum-card"><div className="udhaari-sum-label">{label}</div><div className="udhaari-sum-value">{value}</div></div>;
}

function OrderDrawer({ order, audit, onClose }: { order: Order; audit: AuditEvent[]; onClose: () => void }) {
  return (
    <aside className="drawer">
      <button className="drawer-close" onClick={onClose}>×</button>
      <h2>Order #{order.id}</h2>
      <p className="dashboard-subtitle">Raw: {order.message?.raw_text ?? "—"}</p>
      <p className="dashboard-subtitle">Extracted: {order.message?.extracted_text ?? "—"}</p>
      <p className="dashboard-subtitle">Notes: {order.notes ?? "—"}</p>
      <h3>Items</h3>
      {order.items.map((item) => <div className="drawer-row" key={item.id}>{item.name} · {item.quantity}{item.unit} · {(item.confidence * 100).toFixed(0)}%</div>)}
      <h3>Audit trail</h3>
      {audit.map((event) => <div className="drawer-row" key={event.id}><strong>{event.action}</strong><br />{new Date(event.created_at).toLocaleString("en-IN")}<br />{event.evidence}</div>)}
      {audit.length === 0 && <div className="drawer-row">No audit events yet.</div>}
    </aside>
  );
}

export default App;
