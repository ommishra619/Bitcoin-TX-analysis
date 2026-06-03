import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import Chart from "chart.js/auto";
import "./styles.css";

const API_BASE = "http://localhost:8000";
const CURRENCIES = ["usd", "eur", "gbp", "inr", "jpy", "cad", "aud"];

function sma(series, period) {
  const out = Array(series.length).fill(null);
  let sum = 0;
  for (let i = 0; i < series.length; i += 1) {
    sum += series[i];
    if (i >= period) sum -= series[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

function ema(series, period) {
  const out = Array(series.length).fill(null);
  const k = 2 / (period + 1);
  let prev = null;
  for (let i = 0; i < series.length; i += 1) {
    prev = prev == null ? series[i] : series[i] * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

function rsi(series, period = 14) {
  const out = Array(series.length).fill(null);
  if (series.length <= period) return out;

  let gain = 0;
  let loss = 0;

  for (let i = 1; i <= period; i += 1) {
    const d = series[i] - series[i - 1];
    if (d >= 0) gain += d;
    else loss -= d;
  }

  gain /= period;
  loss /= period;
  out[period] = loss === 0 ? 100 : 100 - 100 / (1 + gain / loss);

  for (let i = period + 1; i < series.length; i += 1) {
    const d = series[i] - series[i - 1];
    gain = (gain * (period - 1) + Math.max(0, d)) / period;
    loss = (loss * (period - 1) + Math.max(0, -d)) / period;
    out[i] = loss === 0 ? 100 : 100 - 100 / (1 + gain / loss);
  }

  return out;
}

function macd(series, fast = 12, slow = 26, signal = 9) {
  const fastEma = ema(series, fast);
  const slowEma = ema(series, slow);
  const macdLine = series.map((_, i) => fastEma[i] - slowEma[i]);
  const signalLine = ema(macdLine, signal);
  const hist = macdLine.map((v, i) => v - signalLine[i]);
  return { macdLine, signalLine, hist };
}

function detectPeaksValleys(series, look = 2) {
  const peaks = [];
  const valleys = [];
  for (let i = look; i < series.length - look; i += 1) {
    let isPeak = true;
    let isValley = true;
    for (let j = i - look; j <= i + look; j += 1) {
      if (j === i) continue;
      if (series[i] <= series[j]) isPeak = false;
      if (series[i] >= series[j]) isValley = false;
    }
    if (isPeak) peaks.push(i);
    if (isValley) valleys.push(i);
  }
  return { peaks, valleys };
}

function App() {
  const [currency, setCurrency] = useState("usd");
  const [days, setDays] = useState(30);
  const [status, setStatus] = useState("Loading data...");
  const [error, setError] = useState("");
  const [prices, setPrices] = useState([]);
  const [labels, setLabels] = useState([]);
  const [alerts, setAlerts] = useState([]);

  const [showSma, setShowSma] = useState(true);
  const [showEma, setShowEma] = useState(true);
  const [showRsi, setShowRsi] = useState(true);
  const [showMacd, setShowMacd] = useState(true);

  const [drawMode, setDrawMode] = useState("none");

  const priceCanvasRef = useRef(null);
  const drawCanvasRef = useRef(null);
  const rsiCanvasRef = useRef(null);
  const macdCanvasRef = useRef(null);

  const priceChartRef = useRef(null);
  const rsiChartRef = useRef(null);
  const macdChartRef = useRef(null);

  const drawingsRef = useRef({ trendlines: [], notes: [] });
  const pendingStartRef = useRef(null);

  const money = useMemo(
    () =>
      new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: currency.toUpperCase()
      }),
    [currency]
  );

  const sentiment = useMemo(() => {
    if (prices.length < 26) return null;

    const latestPrice = prices[prices.length - 1];
    
    // Calculate SMA
    const smaVals = sma(prices, 20);
    const latestSma = smaVals[smaVals.length - 1];

    // Calculate EMA
    const emaVals = ema(prices, 20);
    const latestEma = emaVals[emaVals.length - 1];

    // Calculate RSI
    const rsiVals = rsi(prices, 14);
    const latestRsi = rsiVals[rsiVals.length - 1];

    // Calculate MACD
    const { macdLine, signalLine } = macd(prices);
    const latestMacd = macdLine[macdLine.length - 1];
    const latestSignal = signalLine[signalLine.length - 1];

    // Evaluate conditions
    const isEmaBullish = latestPrice > latestEma;
    const isSmaBullish = latestPrice > latestSma;
    
    let rsiStatus = "Neutral";
    let rsiScore = 0;
    if (latestRsi > 70) { rsiStatus = "Overbought"; rsiScore = -1; }
    else if (latestRsi < 30) { rsiStatus = "Oversold"; rsiScore = 1; }

    const isMacdBullish = latestMacd > latestSignal;
    
    // Calculate overall consensus score
    let score = 0;
    if (isEmaBullish) score += 1; else score -= 1;
    if (isSmaBullish) score += 1; else score -= 1;
    if (isMacdBullish) score += 1; else score -= 1;
    score += rsiScore;

    let consensus = "Neutral";
    let consensusClass = "sentiment-neutral";
    if (score >= 2) { consensus = "Strong Buy"; consensusClass = "sentiment-strong-buy"; }
    else if (score === 1) { consensus = "Buy"; consensusClass = "sentiment-buy"; }
    else if (score === -1) { consensus = "Sell"; consensusClass = "sentiment-sell"; }
    else if (score <= -2) { consensus = "Strong Sell"; consensusClass = "sentiment-strong-sell"; }

    const highPrice = Math.max(...prices);
    const lowPrice = Math.min(...prices);

    return {
      latestPrice,
      latestSma,
      latestEma,
      latestRsi,
      latestMacd,
      latestSignal,
      highPrice,
      lowPrice,
      isEmaBullish,
      isSmaBullish,
      rsiStatus,
      isMacdBullish,
      consensus,
      consensusClass,
      score
    };
  }, [prices]);

  async function fetchData() {
    setError("");
    setStatus(`Loading ${days}d BTC data in ${currency.toUpperCase()}...`);

    const res = await fetch(`${API_BASE}/api/price?days=${days}&currency=${currency}`);
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(payload.detail || "Failed to fetch price data");

    const points = payload?.history?.prices || [];
    const nextLabels = points.map(([ts]) => new Date(ts).toLocaleDateString());
    const nextPrices = points.map(([, p]) => Number(p));

    setLabels(nextLabels);
    setPrices(nextPrices);

    const spot = payload?.spot?.price;
    setStatus(
      spot != null
        ? `Spot BTC price: ${money.format(spot)} | Points: ${nextPrices.length}`
        : `Points: ${nextPrices.length}`
    );
  }

  function resizeDrawLayer() {
    if (!priceCanvasRef.current || !drawCanvasRef.current) return;
    const rect = priceCanvasRef.current.getBoundingClientRect();
    const drawCanvas = drawCanvasRef.current;
    drawCanvas.width = Math.max(1, Math.floor(rect.width));
    drawCanvas.height = Math.max(1, Math.floor(rect.height));
    drawCanvas.style.width = `${rect.width}px`;
    drawCanvas.style.height = `${rect.height}px`;
    redrawOverlay();
  }

  function toCanvasPixel(point) {
    const chart = priceChartRef.current;
    if (!chart) return { x: 0, y: 0 };
    const x = chart.scales.x.getPixelForValue(point.xVal);
    const y = chart.scales.y.getPixelForValue(point.yVal);
    return { x, y };
  }

  function redrawOverlay() {
    const drawCanvas = drawCanvasRef.current;
    const chart = priceChartRef.current;
    if (!drawCanvas || !chart) return;

    const ctx = drawCanvas.getContext("2d");
    ctx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);

    ctx.lineWidth = 2;
    ctx.strokeStyle = "#f97316";
    drawingsRef.current.trendlines.forEach((line) => {
      const a = toCanvasPixel(line.a);
      const b = toCanvasPixel(line.b);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    });

    ctx.fillStyle = "#fde68a";
    ctx.font = "12px Segoe UI";
    drawingsRef.current.notes.forEach((note) => {
      const p = toCanvasPixel(note.p);
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillText(note.text, p.x + 8, p.y - 8);
    });

    if (pendingStartRef.current) {
      const p = toCanvasPixel(pendingStartRef.current);
      ctx.fillStyle = "#fb7185";
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  useEffect(() => {
    function onResize() {
      resizeDrawLayer();
    }
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    async function run() {
      try {
        await fetchData();
      } catch (err) {
        setStatus("Request failed");
        setError(err.message || "Failed to load dashboard data");
      }
    }
    run();
  }, [currency, days]);

  useEffect(() => {
    if (!prices.length || !labels.length || !priceCanvasRef.current) return;

    const chart = priceChartRef.current;
    if (chart) chart.destroy();

    const sma20 = sma(prices, 20);
    const ema20 = ema(prices, 20);
    const extrema = detectPeaksValleys(prices, 2);

    const peaks = extrema.peaks.map((i) => ({ x: labels[i], y: prices[i] }));
    const valleys = extrema.valleys.map((i) => ({ x: labels[i], y: prices[i] }));

    const nextAlerts = [];
    extrema.peaks.slice(-4).forEach((i) => nextAlerts.push(`Peak: ${labels[i]} at ${money.format(prices[i])}`));
    extrema.valleys.slice(-4).forEach((i) => nextAlerts.push(`Valley: ${labels[i]} at ${money.format(prices[i])}`));
    setAlerts(nextAlerts.length ? nextAlerts : ["No strong peak/valley alerts in this timeframe."]);

    priceChartRef.current = new Chart(priceCanvasRef.current.getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: `BTC (${currency.toUpperCase()})`,
            data: prices,
            borderColor: "#25c2ff",
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.15,
            fill: true,
            backgroundColor: (context) => {
              const chart = context.chart;
              const {ctx, chartArea} = chart;
              if (!chartArea) return null;
              const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
              gradient.addColorStop(0, 'rgba(37, 194, 255, 0.2)');
              gradient.addColorStop(1, 'rgba(37, 194, 255, 0.0)');
              return gradient;
            }
          },
          {
            label: "SMA(20)",
            data: sma20,
            borderColor: "#f59e0b",
            borderWidth: 1.5,
            pointRadius: 0,
            borderDash: [5, 4],
            hidden: !showSma
          },
          {
            label: "EMA(20)",
            data: ema20,
            borderColor: "#ec4899",
            borderWidth: 1.5,
            pointRadius: 0,
            hidden: !showEma
          },
          {
            label: "Peaks",
            data: peaks,
            parsing: false,
            pointRadius: 5,
            showLine: false,
            borderColor: "#ef4444",
            backgroundColor: "#ef4444"
          },
          {
            label: "Valleys",
            data: valleys,
            parsing: false,
            pointRadius: 5,
            showLine: false,
            borderColor: "#10b981",
            backgroundColor: "#10b981"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { color: "#dbe7ff", font: { family: "Plus Jakarta Sans" } } },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${money.format(ctx.parsed.y)}`
            }
          }
        },
        scales: {
          x: { ticks: { color: "#94a3b8", maxTicksLimit: 10, font: { family: "Plus Jakarta Sans" } }, grid: { color: "rgba(148,163,184,0.05)" } },
          y: { ticks: { color: "#94a3b8", font: { family: "Plus Jakarta Sans" } }, grid: { color: "rgba(148,163,184,0.05)" } }
        },
        animation: {
          onComplete: () => redrawOverlay()
        }
      }
    });

    resizeDrawLayer();
    return () => priceChartRef.current && priceChartRef.current.destroy();
  }, [prices, labels, currency, money, showSma, showEma]);

  useEffect(() => {
    if (!prices.length || !labels.length || !rsiCanvasRef.current) return;

    if (rsiChartRef.current) rsiChartRef.current.destroy();
    const rsiData = rsi(prices, 14);
    rsiChartRef.current = new Chart(rsiCanvasRef.current.getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [
          { 
            label: "RSI(14)", 
            data: rsiData, 
            borderColor: "#10b981", 
            borderWidth: 2,
            pointRadius: 0, 
            hidden: !showRsi,
            fill: true,
            backgroundColor: (context) => {
              const chart = context.chart;
              const {ctx, chartArea} = chart;
              if (!chartArea) return null;
              const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
              gradient.addColorStop(0, 'rgba(16, 185, 129, 0.08)');
              gradient.addColorStop(1, 'rgba(16, 185, 129, 0.00)');
              return gradient;
            }
          },
          { label: "Overbought 70", data: labels.map(() => 70), borderColor: "rgba(239, 68, 68, 0.4)", pointRadius: 0, borderDash: [4, 4] },
          { label: "Oversold 30", data: labels.map(() => 30), borderColor: "rgba(59, 130, 246, 0.4)", pointRadius: 0, borderDash: [4, 4] }
        ]
      },
      options: {
        plugins: { legend: { labels: { color: "#dbe7ff", font: { family: "Plus Jakarta Sans" } } } },
        scales: {
          x: { display: false },
          y: { min: 0, max: 100, ticks: { color: "#94a3b8", font: { family: "Plus Jakarta Sans" } }, grid: { color: "rgba(148,163,184,0.05)" } }
        }
      }
    });

    return () => rsiChartRef.current && rsiChartRef.current.destroy();
  }, [prices, labels, showRsi]);

  useEffect(() => {
    if (!prices.length || !labels.length || !macdCanvasRef.current) return;

    if (macdChartRef.current) macdChartRef.current.destroy();
    const { macdLine, signalLine, hist } = macd(prices);

    macdChartRef.current = new Chart(macdCanvasRef.current.getContext("2d"), {
      data: {
        labels,
        datasets: [
          {
            type: "bar",
            label: "Histogram",
            data: hist,
            backgroundColor: hist.map((v) => (v >= 0 ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)")),
            hidden: !showMacd
          },
          { type: "line", label: "MACD", data: macdLine, borderColor: "#f59e0b", borderWidth: 1.5, pointRadius: 0, hidden: !showMacd },
          { type: "line", label: "Signal", data: signalLine, borderColor: "#3b82f6", borderWidth: 1.5, pointRadius: 0, hidden: !showMacd }
        ]
      },
      options: {
        plugins: { legend: { labels: { color: "#dbe7ff", font: { family: "Plus Jakarta Sans" } } } },
        scales: {
          x: { display: false },
          y: { ticks: { color: "#94a3b8", font: { family: "Plus Jakarta Sans" } }, grid: { color: "rgba(148,163,184,0.05)" } }
        }
      }
    });

    return () => macdChartRef.current && macdChartRef.current.destroy();
  }, [prices, labels, showMacd]);

  function handleOverlayClick(evt) {
    if (!priceChartRef.current || drawMode === "none") return;

    const rect = drawCanvasRef.current.getBoundingClientRect();
    const x = evt.clientX - rect.left;
    const y = evt.clientY - rect.top;

    const xVal = priceChartRef.current.scales.x.getValueForPixel(x);
    const yVal = priceChartRef.current.scales.y.getValueForPixel(y);
    const point = { xVal, yVal };

    if (drawMode === "trendline") {
      if (!pendingStartRef.current) pendingStartRef.current = point;
      else {
        drawingsRef.current.trendlines.push({ a: pendingStartRef.current, b: point });
        pendingStartRef.current = null;
      }
      redrawOverlay();
      return;
    }

    if (drawMode === "annotate") {
      const text = window.prompt("Annotation text:");
      if (text && text.trim()) {
        drawingsRef.current.notes.push({ p: point, text: text.trim() });
        redrawOverlay();
      }
    }
  }

  function exportCsv() {
    if (!prices.length) return;
    const rows = ["date,price"];
    for (let i = 0; i < labels.length; i += 1) rows.push(`${labels[i]},${prices[i]}`);
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `btc-price-${currency}-${days}d.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="wrap">
      <header className="landing-nav" style={{margin: "0 0 32px 0", maxWidth: "100%", background: "var(--card)", borderColor: "var(--border)"}}>
        <div className="landing-logo" style={{color: "var(--text)", display: "flex", alignItems:"center", gap: "10px"}}>
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg>
          <strong style={{fontSize: "16px"}}>TxIntel / Graph Panel</strong>
        </div>
        <nav className="landing-links" style={{display: "none"}}>
        </nav>
        <div className="landing-nav-actions">
          <a className="btn" href="/">Main</a>
          <a className="btn" href="/tx-alert.html">Early Alerts</a>
        </div>
      </header>

      <div style={{marginBottom: "24px"}}>
        <h1 style={{margin: 0, fontSize: "32px", letterSpacing: "-0.02em", color: "#fff"}}>Bitcoin Price Analysis Dashboard</h1>
        <div className="sub" style={{fontSize: "15px", marginTop: "8px", maxWidth: "600px"}}>
          Interactive chart with indicators, trendlines, annotations, pattern markers, and currency switching.
        </div>
      </div>

      {sentiment && (
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-label">Spot Price</div>
            <div className="metric-value value-glow">{money.format(sentiment.latestPrice)}</div>
            <div className="metric-trend green">Live Market Spot</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Timeframe High</div>
            <div className="metric-value">{money.format(sentiment.highPrice)}</div>
            <div className="metric-trend green">Timeframe Peak</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Timeframe Low</div>
            <div className="metric-value">{money.format(sentiment.lowPrice)}</div>
            <div className="metric-trend red">Timeframe Floor</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Market Consensus</div>
            <div className={`metric-value ${sentiment.consensusClass}`}>{sentiment.consensus}</div>
            <div className="metric-trend">Combined TA Signal</div>
          </div>
        </div>
      )}

      <div className="card controls">
        <div className="span-6">
          <div className="label">Currency</div>
          <div className="row">
            {CURRENCIES.map((c) => (
              <button key={c} className={currency === c ? "active" : ""} onClick={() => setCurrency(c)}>
                {c.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="span-6">
          <div className="label">Timeframe</div>
          <div className="row">
            <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
              <option value={180}>180 days</option>
              <option value={365}>365 days</option>
            </select>
            <button onClick={fetchData}>Refresh</button>
          </div>
        </div>

        <div className="span-6">
          <div className="label">Indicators</div>
          <div className="row">
            <label><input type="checkbox" checked={showSma} onChange={(e) => setShowSma(e.target.checked)} /> SMA(20)</label>
            <label><input type="checkbox" checked={showEma} onChange={(e) => setShowEma(e.target.checked)} /> EMA(20)</label>
            <label><input type="checkbox" checked={showRsi} onChange={(e) => setShowRsi(e.target.checked)} /> RSI(14)</label>
            <label><input type="checkbox" checked={showMacd} onChange={(e) => setShowMacd(e.target.checked)} /> MACD(12,26,9)</label>
          </div>
        </div>

        <div className="span-6">
          <div className="label">Tools</div>
          <div className="row">
            <button className={drawMode === "trendline" ? "active" : ""} onClick={() => setDrawMode(drawMode === "trendline" ? "none" : "trendline")}>Draw Trendline</button>
            <button className={drawMode === "annotate" ? "active" : ""} onClick={() => setDrawMode(drawMode === "annotate" ? "none" : "annotate")}>Add Annotation</button>
            <button
              onClick={() => {
                drawingsRef.current = { trendlines: [], notes: [] };
                pendingStartRef.current = null;
                redrawOverlay();
              }}
            >
              Clear Drawings
            </button>
            <button onClick={exportCsv}>Export CSV</button>
            <button onClick={() => window.print()}>Export PDF</button>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="status">{status}</div>
        {error ? <div className="error">{error}</div> : null}
        <div className="chart-wrap">
          <canvas ref={priceCanvasRef} />
          <canvas id="drawLayer" ref={drawCanvasRef} onClick={handleOverlayClick} />
        </div>
      </div>

      <div className="split">
        <div className="card">
          <div className="label">RSI</div>
          <canvas ref={rsiCanvasRef} height="160" />
        </div>
        <div className="card">
          <div className="label">MACD</div>
          <canvas ref={macdCanvasRef} height="160" />
        </div>
      </div>

      <div className="card">
        <div className="label">Pattern Alerts (Peak/Valley Detection)</div>
        <ul className="alerts">
          {alerts.map((a, idx) => (
            <li key={`${a}-${idx}`}>{a}</li>
          ))}
        </ul>
      </div>

      {sentiment && (
        <div className="card forensics-panel">
          <div className="label" style={{ marginBottom: "16px" }}>Technical Indicator Forensics</div>
          <div className="forensics-grid">
            <div className="forensics-item">
              <span className="item-title">EMA(20) Trend Analysis</span>
              <span className={`item-value ${sentiment.isEmaBullish ? "green" : "red"}`}>
                {sentiment.isEmaBullish ? "🟢 Bullish Trend" : "🔴 Bearish Trend"}
              </span>
              <p className="item-desc">Price is trading {sentiment.isEmaBullish ? "above" : "below"} the 20-period Exponential Moving Average ({money.format(sentiment.latestEma)}).</p>
            </div>
            
            <div className="forensics-item">
              <span className="item-title">SMA(20) Support/Resistance</span>
              <span className={`item-value ${sentiment.isSmaBullish ? "green" : "red"}`}>
                {sentiment.isSmaBullish ? "🟢 Above Support" : "🔴 Below Resistance"}
              </span>
              <p className="item-desc">Price is trading {sentiment.isSmaBullish ? "above" : "below"} the Simple Moving Average ({money.format(sentiment.latestSma)}).</p>
            </div>

            <div className="forensics-item">
              <span className="item-title">RSI Momentum Oscillator</span>
              <span className={`item-value ${sentiment.rsiStatus === "Overbought" ? "red" : sentiment.rsiStatus === "Oversold" ? "green" : "blue"}`}>
                📊 {sentiment.latestRsi ? `${sentiment.latestRsi.toFixed(2)} (${sentiment.rsiStatus})` : "N/A"}
              </span>
              <p className="item-desc">RSI value is {sentiment.rsiStatus.toLowerCase()}. Values over 70 imply overbought conditions, while values under 30 imply oversold.</p>
            </div>

            <div className="forensics-item">
              <span className="item-title">MACD Trend Momentum</span>
              <span className={`item-value ${sentiment.isMacdBullish ? "green" : "red"}`}>
                ⚡ {sentiment.isMacdBullish ? "Bullish Momentum" : "Bearish Momentum"}
              </span>
              <p className="item-desc">MACD line ({sentiment.latestMacd ? sentiment.latestMacd.toFixed(2) : "N/A"}) is trading {sentiment.isMacdBullish ? "above" : "below"} the signal line ({sentiment.latestSignal ? sentiment.latestSignal.toFixed(2) : "N/A"}).</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
