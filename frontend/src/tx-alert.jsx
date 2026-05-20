import React, { useMemo, useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import CytoscapeComponent from "react-cytoscapejs";
import "./styles.css";

const API_BASE = "http://localhost:8000";
const TXID_RE = /^[0-9a-fA-F]{64}$/;
const ADDRESS_RE = /^(bc1|tb1|[13mn2])[a-zA-HJ-NP-Z0-9]{20,90}$/;

function parseInputItems(raw) {
  return raw
    .split(/[\s,]+/)
    .map((v) => v.trim())
    .filter(Boolean);
}

function classifyInput(items) {
  const txids = [];
  const addresses = [];
  const invalid = [];

  items.forEach((item) => {
    if (TXID_RE.test(item)) txids.push(item.toLowerCase());
    else if (ADDRESS_RE.test(item)) addresses.push(item);
    else invalid.push(item);
  });

  if (!items.length) return { mode: "empty", txids, addresses, invalid };
  if (invalid.length) return { mode: "invalid", txids, addresses, invalid };
  if (txids.length && !addresses.length) return { mode: "txids", txids, addresses, invalid };
  if (addresses.length === 1 && !txids.length) return { mode: "address", txids, addresses, invalid };
  if (addresses.length > 1 && !txids.length) return { mode: "addresses", txids, addresses, invalid };
  return { mode: "mixed", txids, addresses, invalid };
}

function summarizeEarlyAlerts(result) {
  const alerts = [];
  const patterns = result?.behavior_patterns || [];
  const counts = result?.classification_counts || {};
  const riskScore = result?.risk?.score;

  if (typeof riskScore === "number") {
    if (riskScore >= 70) alerts.push({ level: "high", text: `High risk score detected (${riskScore}/100).` });
    else if (riskScore >= 45) alerts.push({ level: "medium", text: `Elevated risk score detected (${riskScore}/100).` });
  }

  const suspiciousPattern = patterns.find((p) => /(peeling|batch|mix|suspicious|chain|rapid|launder|ransom)/i.test(p));
  if (suspiciousPattern) {
    alerts.push({
      level: "medium",
      text: `Behavior pattern requires review: ${suspiciousPattern}`
    });
  }

  const flaggedClass = Object.entries(counts).find(([name, count]) => count > 0 && /(exchange|peeling|anomal|suspicious)/i.test(name));
  if (flaggedClass) {
    alerts.push({
      level: "medium",
      text: `Detected classified signal: ${flaggedClass[0]} (${flaggedClass[1]}).`
    });
  }

  if ((result?.tx_count || 0) >= 25) {
    alerts.push({ level: "low", text: `Large submitted transaction batch analyzed (${result.tx_count}).` });
  }

  if (!alerts.length) {
    alerts.push({
      level: "low",
      text: "No critical early warnings were triggered for this batch. Continue with manual review."
    });
  }

  return alerts;
}

function TransactionGraph({ graphData }) {
  const containerRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const elements = useMemo(() => {
    if (!graphData) return [];
    
    // Max centrality for scaling sizes
    const maxC = Math.max(...(graphData.nodes || []).map(n => n.centrality || 0));

    const nodes = (graphData.nodes || []).map(n => ({
      data: {
        id: n.id,
        label: n.id.substring(0, 10) + '...',
        val: n.centrality || 0,
        type: (n.centrality || 0) > 0.5 ? 'flagged' : 'normal',
        score: maxC ? (n.centrality || 0) / maxC : 0
      }
    }));
    
    const edges = (graphData.edges || []).map((e, index) => ({
      data: {
        id: `e${index}`,
        source: e.source,
        target: e.target
      }
    }));

    return [...nodes, ...edges];
  }, [graphData]);

  const style = useMemo(() => [
    {
      selector: 'node',
      style: {
        'background-color': '#25c2ff',
        'label': 'data(label)',
        'color': '#fff',
        'font-family': 'Inter, sans-serif',
        'font-size': '10px',
        'text-valign': 'top',
        'text-margin-y': -5,
        'width': 'mapData(score, 0, 1, 16, 40)',
        'height': 'mapData(score, 0, 1, 16, 40)',
        'text-background-color': 'rgba(0,0,0,0.6)',
        'text-background-opacity': 1,
        'text-background-padding': '4px',
        'text-background-shape': 'roundrectangle'
      }
    },
    {
      selector: 'node[type="flagged"]',
      style: {
        'background-color': '#ef4444',
        'shape': 'hexagon',
        'width': 'mapData(score, 0, 1, 24, 48)',
        'height': 'mapData(score, 0, 1, 24, 48)'
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': 'rgba(110, 231, 255, 0.25)',
        'target-arrow-color': 'rgba(110, 231, 255, 0.4)',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'arrow-scale': 1.2
      }
    }
  ], []);

  const handleFullscreen = () => {
    const elem = containerRef.current;
    if (!elem) return;
    if (!document.fullscreenElement) {
      elem.requestFullscreen().then(() => setIsFullscreen(true));
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false));
    }
  };

  if (!graphData) return null;

  return (
    <div className="card" ref={containerRef} style={{ background: isFullscreen ? '#09090b' : 'var(--card)', padding: 0, overflow: "hidden" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 20px" }}>
        <div className="label">Cytoscape Network Graph</div>
        <button
          onClick={handleFullscreen}
          style={{ background: "#ff5a1f", color: "#fff", border: "none" }}
        >
          {isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
        </button>
      </div>
      <div style={{ height: isFullscreen ? "100vh" : "540px", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
        <CytoscapeComponent 
          elements={elements} 
          stylesheet={style}
          layout={{ name: 'cose', animate: false, nodeRepulsion: 400000, idealEdgeLength: 60, edgeElasticity: 100 }}
          style={{ width: '100%', height: '100%' }} 
          minZoom={0.2}
          maxZoom={3}
          wheelSensitivity={0.2}
        />
      </div>
      <div className="hint" style={{ padding: "12px 20px" }}>
        <strong>Powered by Cytoscape.js:</strong> Enterprise-grade clustering. Scroll to zoom. High centrality = Red Hexagon.
      </div>
    </div>
  );
}

function TransactionList({ transactions, isScam }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState("index");

  const filteredTxs = useMemo(() => {
    let filtered = transactions || [];
    
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (tx) =>
          tx.txid?.toLowerCase().includes(term) ||
          tx.inputs?.some((i) => i.address?.toLowerCase().includes(term)) ||
          tx.outputs?.some((o) => o.address?.toLowerCase().includes(term))
      );
    }

    // Sort
    return filtered.sort((a, b) => {
      if (sortBy === "inputs") return (b.inputs?.length || 0) - (a.inputs?.length || 0);
      if (sortBy === "outputs") return (b.outputs?.length || 0) - (a.outputs?.length || 0);
      if (sortBy === "value") {
        const aVal = a.outputs?.reduce((s, o) => s + (o.value || 0), 0) || 0;
        const bVal = b.outputs?.reduce((s, o) => s + (o.value || 0), 0) || 0;
        return bVal - aVal;
      }
      return 0;
    });
  }, [transactions, searchTerm, sortBy]);

  if (!transactions || transactions.length === 0) {
    return null;
  }

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <div className="label">Transaction Details ({filteredTxs.length})</div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            style={{
              background: "rgba(10, 24, 44, 0.9)",
              color: "#dbe7ff",
              border: "1px solid rgba(148, 163, 184, 0.25)",
              borderRadius: "6px",
              padding: "4px 8px",
              fontSize: "12px",
              cursor: "pointer"
            }}
          >
            <option value="index">By Index</option>
            <option value="inputs">By Inputs</option>
            <option value="outputs">By Outputs</option>
            <option value="value">By Value</option>
          </select>
          <input
            type="text"
            placeholder="Search address or txid..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              background: "rgba(10, 24, 44, 0.9)",
              color: "#dbe7ff",
              border: "1px solid rgba(148, 163, 184, 0.25)",
              borderRadius: "6px",
              padding: "6px 10px",
              fontSize: "12px",
              minWidth: "200px"
            }}
          />
        </div>
      </div>

      <div style={{ overflowX: "auto", maxHeight: "600px", overflowY: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
          <thead style={{ position: "sticky", top: 0, background: "rgba(17, 31, 52, 0.9)" }}>
            <tr style={{ borderBottom: "2px solid #25c2ff" }}>
              <th style={{ padding: "10px", textAlign: "left", color: "#67e8f9" }}>TXID</th>
              <th style={{ padding: "10px", textAlign: "center", color: "#67e8f9" }}>Inputs</th>
              <th style={{ padding: "10px", textAlign: "center", color: "#67e8f9" }}>Outputs</th>
              <th style={{ padding: "10px", textAlign: "right", color: "#67e8f9" }}>Total Value (BTC)</th>
              <th style={{ padding: "10px", textAlign: "left", color: "#67e8f9" }}>From Address</th>
              <th style={{ padding: "10px", textAlign: "left", color: "#67e8f9" }}>To Address</th>
            </tr>
          </thead>
          <tbody>
            {filteredTxs.map((tx, idx) => {
              const totalIn = (tx.inputs || []).reduce((s, i) => s + (i.value || 0), 0);
              const totalOut = (tx.outputs || []).reduce((s, o) => s + (o.value || 0), 0);
              const fromAddr = tx.inputs?.[0]?.address || "unknown";
              const toAddr = tx.outputs?.[0]?.address || "unknown";
              const isOrigin = isScam && transactions.indexOf(tx) === 0;

              return (
                <tr
                  key={idx}
                  style={{
                    borderBottom: "1px solid rgba(148, 163, 184, 0.15)",
                    backgroundColor: idx % 2 === 0 ? "transparent" : "rgba(96, 160, 255, 0.05)",
                    transition: "background-color 0.2s"
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.backgroundColor = "rgba(96, 160, 255, 0.15)")}
                  onMouseOut={(e) =>
                    (e.currentTarget.style.backgroundColor =
                      idx % 2 === 0 ? "transparent" : "rgba(96, 160, 255, 0.05)")
                  }
                >
                  <td
                    style={{ padding: "10px", fontFamily: "monospace", color: "#25c2ff", cursor: "pointer", whiteSpace: "nowrap" }}
                    title={tx.txid}
                  >
                    {tx.txid ? tx.txid.substring(0, 16) + "..." : "N/A"}
                    {isOrigin && (
                      <span style={{ backgroundColor: "#ef4444", color: "#fff", fontSize: "9px", padding: "2px 6px", borderRadius: "12px", marginLeft: "8px", fontWeight: "bold", verticalAlign: "middle" }}>
                        SCAM ORIGIN
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "10px", textAlign: "center", color: "#c7d2fe" }}>
                    {tx.inputs?.length || 0}
                  </td>
                  <td style={{ padding: "10px", textAlign: "center", color: "#c7d2fe" }}>
                    {tx.outputs?.length || 0}
                  </td>
                  <td style={{ padding: "10px", textAlign: "right", color: "#a5f3fc", fontWeight: "bold" }}>
                    {totalOut.toFixed(8)}
                  </td>
                  <td
                    style={{ padding: "10px", fontFamily: "monospace", fontSize: "11px", color: "#94a3b8" }}
                    title={fromAddr}
                  >
                    {fromAddr.substring(0, 12)}...
                  </td>
                  <td
                    style={{ padding: "10px", fontFamily: "monospace", fontSize: "11px", color: "#94a3b8" }}
                    title={toAddr}
                  >
                    {toAddr.substring(0, 12)}...
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="hint" style={{ marginTop: "12px" }}>
        Hover over rows for details. Search by address or transaction ID. Sort by number of inputs/outputs or transaction value.
      </div>
    </div>
  );
}

function TxAlertPage() {
  const [rawInput, setRawInput] = useState("");
  const [obsWindow, setObsWindow] = useState("30m");
  const [leadTime, setLeadTime] = useState("5m");
  const [sensitivity, setSensitivity] = useState("high");
  const [status, setStatus] = useState("Select a seed node and define your prediction horizon.");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [transactions, setTransactions] = useState([]);

  const items = useMemo(() => parseInputItems(rawInput), [rawInput]);
  const parsed = useMemo(() => classifyInput(items), [items]);

  async function analyzeTxids() {
    setError("");
    setResult(null);
    setTransactions([]);

    if (parsed.mode === "empty") {
      setError("Add transaction IDs or one Bitcoin address.");
      return;
    }

    if (parsed.mode === "invalid") {
      setError(
        `Found ${parsed.invalid.length} invalid item(s). Use 64-character txids or one valid Bitcoin address.`
      );
      return;
    }

    if (parsed.mode === "mixed") {
      setError("Do not mix txids and addresses in the same run. Submit txids only, or a single address.");
      return;
    }

    if (parsed.mode === "addresses") {
      setError("Only one address is supported per run. For address lists, submit them one at a time.");
      return;
    }

    setLoading(true);
    setStatus(
      parsed.mode === "address"
        ? `Analyzing address ${parsed.addresses[0]}...`
        : `Analyzing ${parsed.txids.length} transaction IDs...`
    );

    try {
      const endpoint = parsed.mode === "address" ? "/api/analyze" : "/api/analyze/txids";
      const body =
        parsed.mode === "address"
          ? {
              address: parsed.addresses[0],
              include_graph: true,
              limit: 100
            }
          : {
              txids: parsed.txids,
              include_graph: true,
              focus_address: focusAddress.trim() || undefined
            };

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });

      const payload = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(payload.detail || "Failed to analyze input.");

      // Extract transactions from graph data if available
      if (payload.graph && payload.graph.edges) {
        const txsFromGraph = payload.graph.edges.map((edge, idx) => ({
          txid: `tx_${idx}`,
          inputs: [{ address: edge.source, value: edge.weight || 0 }],
          outputs: [{ address: edge.target, value: edge.weight || 0 }]
        }));
        setTransactions(txsFromGraph);
      }

      setResult(payload);
      setStatus(
        parsed.mode === "address"
          ? `Address analysis complete (${payload.tx_count} transactions).`
          : `Analysis complete for ${payload.tx_count} transactions.`
      );
    } catch (err) {
      setStatus("Analysis failed.");
      setError(err.message || "Unknown error.");
    } finally {
      setLoading(false);
    }
  }

  async function analyzeFakeTxs() {
    setError("");
    setResult(null);
    setTransactions([]);
    setLoading(true);
    setStatus("Analyzing fake generated transactions...");

    try {
      const res = await fetch(`${API_BASE}/api/analyze/fake`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      const payload = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(payload.detail || "Failed to analyze fake transactions.");

      // Extract transactions from graph data if available
      if (payload.graph && payload.graph.edges) {
        const txsFromGraph = payload.graph.edges.map((edge, idx) => ({
          txid: `fake_tx_${idx}`,
          inputs: [{ address: edge.source, value: edge.weight || 0 }],
          outputs: [{ address: edge.target, value: edge.weight || 0 }]
        }));
        setTransactions(txsFromGraph);
      }

      setResult(payload);
      setStatus(`Fake transaction analysis complete (${payload.tx_count} transactions).`);
    } catch (err) {
      setStatus("Analysis failed.");
      setError(err.message || "Unknown error.");
    } finally {
      setLoading(false);
    }
  }

  const alerts = useMemo(() => (result ? summarizeEarlyAlerts(result) : []), [result]);

  return (
    <div className="wrap tx-page">
      <div className="title">
        <div>
          <h1>Transaction ID Early Alert Page</h1>
          <div className="sub">
            Paste txids from your investigation list, or submit one Bitcoin address, to trigger early warning
            signals.
          </div>
        </div>
        <div className="row">
          <a className="btn" href="/">
            Back to Main
          </a>
          <a className="btn" href="/price-dashboard.html">
            Open Graph Page
          </a>
        </div>
      </div>

      <div className="card tx-form">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
          <div style={{ gridColumn: "1 / -1" }}>
            <div className="label">Target Monitor Node (Seed Address)</div>
            <input
              type="text"
              placeholder="Paste the Bitcoin address to monitor (e.g. bc1... or 1...)"
              value={rawInput}
              onChange={(e) => setRawInput(e.target.value)}
              disabled={loading}
              style={{ padding: "12px", width: "100%", borderRadius: "8px", border: "1px solid var(--border)", background: "rgba(0,0,0,0.2)", color: "#fff", boxSizing: "border-box" }}
            />
            <div className="hint" style={{ marginTop: "8px" }}>
              The central node from which to extract the transaction subgraph.
            </div>
          </div>

          <div>
            <div className="label">Observation Window (H_obs)</div>
            <select
              value={obsWindow}
              onChange={(e) => setObsWindow(e.target.value)}
              disabled={loading}
              style={{ padding: "12px", width: "100%", borderRadius: "8px", border: "1px solid var(--border)", background: "rgba(0,0,0,0.2)", color: "#fff" }}
            >
              <option value="5m" style={{background: "#18181b"}}>Past 5 Minutes</option>
              <option value="10m" style={{background: "#18181b"}}>Past 10 Minutes</option>
              <option value="15m" style={{background: "#18181b"}}>Past 15 Minutes</option>
              <option value="30m" style={{background: "#18181b"}}>Past 30 Minutes</option>
              <option value="60m" style={{background: "#18181b"}}>Past 60 Minutes</option>
            </select>
          </div>

          <div>
            <div className="label">Prediction Lead Time (L)</div>
            <select
              value={leadTime}
              onChange={(e) => setLeadTime(e.target.value)}
              disabled={loading}
              style={{ padding: "12px", width: "100%", borderRadius: "8px", border: "1px solid var(--border)", background: "rgba(0,0,0,0.2)", color: "#fff" }}
            >
              <option value="5m" style={{background: "#18181b"}}>5 Minutes Early Warning</option>
              <option value="10m" style={{background: "#18181b"}}>10 Minutes Early Warning</option>
              <option value="15m" style={{background: "#18181b"}}>15 Minutes Early Warning</option>
              <option value="30m" style={{background: "#18181b"}}>30 Minutes Early Warning</option>
              <option value="60m" style={{background: "#18181b"}}>60 Minutes Early Warning</option>
            </select>
          </div>

          <div style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(0,0,0,0.2)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border)" }}>
            <div>
               <div className="label" style={{ marginBottom: "0" }}>Sensitivity Profile</div>
               <div className="hint">Trades off lead time prediction accuracy against false positive rate.</div>
            </div>
            <div style={{ display: "flex", gap: "10px" }}>
               <button onClick={() => setSensitivity("high")} style={{ cursor: "pointer", background: sensitivity === "high" ? "#ef4444" : "transparent", color: "#fff", border: "1px solid #ef4444", padding: "6px 12px", borderRadius: "6px", fontSize: "12px" }}>High Sensitivity</button>
               <button onClick={() => setSensitivity("precision")} style={{ cursor: "pointer", background: sensitivity === "precision" ? "#22c55e" : "transparent", color: "#fff", border: "1px solid #22c55e", padding: "6px 12px", borderRadius: "6px", fontSize: "12px" }}>High Precision</button>
            </div>
          </div>
        </div>

        <div className="row" style={{ marginTop: "24px", paddingTop: "24px", borderTop: "1px solid var(--border)" }}>
          <button onClick={analyzeTxids} disabled={loading} style={{ padding: "12px 24px", fontSize: "14px" }}>
            {loading ? "Extracting Subgraph & Predicting..." : "Extract Subgraph & Predict State"}
          </button>
          <button onClick={analyzeFakeTxs} disabled={loading} style={{ background: "#4bc9ff", color: "#000", padding: "12px 24px", fontSize: "14px" }}>
            Test model with synthesized data
          </button>
        </div>
      </div>

      <div className="card">
        <div className="status">{status}</div>
        {error ? <div className="error">{error}</div> : null}
      </div>

      {result ? (
        <>
          <div className="card">
            <div className="label">Early Alerts</div>
            <ul className="alerts">
              {alerts.map((alert, idx) => (
                <li key={`${alert.text}-${idx}`} className={`alert-${alert.level}`}>
                  {alert.text}
                </li>
              ))}
            </ul>
          </div>

          {result.graph ? <TransactionGraph graphData={result.graph} /> : null}

          <TransactionList transactions={transactions} isScam={result?.risk?.score >= 50} />

          <div className="tx-grid">
            <div className="card">
              <div className="label">Behavior Patterns</div>
              <ul className="alerts">
                {(result.behavior_patterns || []).map((pattern, idx) => (
                  <li key={`${pattern}-${idx}`}>{pattern}</li>
                ))}
              </ul>
            </div>

            <div className="card">
              <div className="label">Classification Counts</div>
              <ul className="alerts">
                {Object.entries(result.classification_counts || {}).map(([name, count]) => (
                  <li key={name}>
                    {name}: {count}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {result.risk ? (
            <div className="card">
              <div className="label">Risk Score</div>
              <h2 className="risk-score">{result.risk.score}/100</h2>
              <ul className="alerts">
                {(result.risk.reasons || []).map((reason, idx) => (
                  <li key={`${reason}-${idx}`}>{reason}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<TxAlertPage />);
