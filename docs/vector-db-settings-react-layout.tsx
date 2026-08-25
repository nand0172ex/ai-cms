import React, { useMemo, useState } from "react";

type Status = "green" | "amber" | "red" | "gray";

type NavKey =
  | "dashboard"
  | "collections"
  | "upload"
  | "sync"
  | "embedding"
  | "search"
  | "monitoring"
  | "help";

const STATUS_COLOR: Record<Status, string> = {
  green: "#1F8F4E",
  amber: "#C88A04",
  red: "#C63131",
  gray: "#6B7280",
};

const navItems: Array<{ key: NavKey; label: string }> = [
  { key: "dashboard", label: "Dashboard" },
  { key: "collections", label: "Collections" },
  { key: "upload", label: "Upload Center" },
  { key: "sync", label: "Data Source Sync" },
  { key: "embedding", label: "Embedding Monitor" },
  { key: "search", label: "Search Playground" },
  { key: "monitoring", label: "System Monitoring" },
  { key: "help", label: "User Help" },
];

function Badge({ status, text }: { status: Status; text: string }) {
  return (
    <span
      style={{
        background: `${STATUS_COLOR[status]}22`,
        color: STATUS_COLOR[status],
        border: `1px solid ${STATUS_COLOR[status]}66`,
        borderRadius: 999,
        padding: "4px 10px",
        fontSize: 12,
        fontWeight: 700,
        textTransform: "uppercase",
      }}
    >
      {text}
    </span>
  );
}

function Card(props: { title: string; children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <section
      style={{
        background: "#FFFFFF",
        border: "1px solid #E5EAF2",
        borderRadius: 12,
        boxShadow: "0 4px 16px rgba(15, 23, 42, 0.06)",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "14px 16px",
          borderBottom: "1px solid #EDF1F7",
        }}
      >
        <h3 style={{ margin: 0, fontSize: 15 }}>{props.title}</h3>
        {props.actions}
      </header>
      <div style={{ padding: 16 }}>{props.children}</div>
    </section>
  );
}

export default function VectorDbSettingsDashboardPage() {
  const [active, setActive] = useState<NavKey>("dashboard");

  const kpis = useMemo(
    () => [
      { label: "Total Collections", value: "27" },
      { label: "Total Vectors", value: "14.8M" },
      { label: "Total Documents", value: "312K" },
      { label: "Qdrant Status", value: "Connected", status: "green" as Status },
    ],
    []
  );

  return (
    <div style={{ minHeight: "100vh", background: "#F5F7FB", color: "#111827" }}>
      <header
        style={{
          height: 64,
          borderBottom: "1px solid #E5EAF2",
          background: "#FFFFFF",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 20px",
          position: "sticky",
          top: 0,
          zIndex: 10,
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 18 }}>Vector DB Settings</h1>
          <p style={{ margin: "2px 0 0", fontSize: 12, color: "#6B7280" }}>Enterprise Operations Dashboard</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Badge status="green" text="Qdrant Connected" />
          <button>Refresh</button>
          <button>Open Logs</button>
        </div>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", minHeight: "calc(100vh - 64px)" }}>
        <aside style={{ borderRight: "1px solid #E5EAF2", background: "#FFFFFF", padding: 12 }}>
          {navItems.map((item) => (
            <button
              key={item.key}
              onClick={() => setActive(item.key)}
              style={{
                width: "100%",
                textAlign: "left",
                marginBottom: 6,
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #E5EAF2",
                background: active === item.key ? "#E8F0FF" : "#FFFFFF",
                fontWeight: active === item.key ? 700 : 500,
                cursor: "pointer",
              }}
            >
              {item.label}
            </button>
          ))}
        </aside>

        <main style={{ padding: 16, display: "grid", gap: 12 }}>
          {active === "dashboard" && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12 }}>
                {kpis.map((kpi) => (
                  <Card key={kpi.label} title={kpi.label}>
                    <div style={{ fontSize: 22, fontWeight: 800 }}>{kpi.value}</div>
                    {"status" in kpi ? <Badge status={kpi.status} text={kpi.value} /> : null}
                  </Card>
                ))}
              </div>
              <Card title="Recent Activities">
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  <li>Collection customer_kb created by admin at 10:21</li>
                  <li>Upload invoice_q2.pdf completed in 43 seconds</li>
                  <li>Sync for CRM API finished with warnings</li>
                </ul>
              </Card>
            </>
          )}

          {active === "collections" && (
            <Card
              title="Collections Management"
              actions={
                <div style={{ display: "flex", gap: 8 }}>
                  <button>Create Collection</button>
                  <button>Refresh</button>
                </div>
              }
            >
              <p>Collection table, health indicators, and statistics drawer appear here.</p>
            </Card>
          )}

          {active === "upload" && (
            <Card title="Data Upload Center">
              <div style={{ border: "2px dashed #B7C6E3", borderRadius: 10, padding: 24, textAlign: "center" }}>
                Drag and drop files here
              </div>
              <p>Queue, progress, and processing statuses render below.</p>
            </Card>
          )}

          {active === "sync" && (
            <Card title="Data Source Sync" actions={<button>Manual Re-Sync</button>}>
              <p>API connection status, last sync time, and sync history table.</p>
            </Card>
          )}

          {active === "embedding" && (
            <Card title="Embedding Monitor">
              <p>Embedding model, chunk count, dimensions, and success or failed counters.</p>
            </Card>
          )}

          {active === "search" && (
            <Card title="Search Playground">
              <input style={{ width: "100%", padding: 10 }} placeholder="Enter semantic query" />
              <p style={{ marginTop: 10 }}>Retrieved chunks with similarity score and source metadata appear here.</p>
            </Card>
          )}

          {active === "monitoring" && (
            <Card title="System Monitoring">
              <p>Connectivity status, collection usage, vector growth trend, and error logs.</p>
            </Card>
          )}

          {active === "help" && (
            <Card title="How it Works">
              <div style={{ display: "grid", gap: 10 }}>
                <div>Document</div>
                <div>Chunking</div>
                <div>Embedding</div>
                <div>Qdrant Storage</div>
                <div>Semantic Search</div>
              </div>
            </Card>
          )}
        </main>
      </div>
    </div>
  );
}
