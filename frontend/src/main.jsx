import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function MainPage() {
  return (
    <div className="landing-wrapper">
      <header className="landing-nav">
        <div className="landing-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg>
        </div>
        <nav className="landing-links">
          <a href="/price-dashboard.html">Graph Panel</a>
          <a href="/tx-alert.html">Early Alerts</a>
          <a href="#">Pricing</a>
          <a href="#">About</a>
          <a href="#">Updates</a>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">API Docs</a>
        </nav>
        <div className="landing-nav-actions">
          <a href="/price-dashboard.html" className="landing-btn-outline">Preview Graph</a>
          <a href="/tx-alert.html" className="landing-btn-primary">Get Started</a>
        </div>
      </header>

      <div className="landing-hero-section">
        <div className="landing-hero-bg-grid"></div>
        <div className="landing-hero-content">
          <div className="landing-badge">
            <span className="landing-badge-icon">✦</span>
            TxIntel - [V1.0]
          </div>
          
          <h1 className="landing-hero-title">
            The intelligence engine that <br/>
            <span className="landing-highlight">exposes & guides.</span>
          </h1>
          
          <p className="landing-hero-subtitle">
            Explore 5000+ transaction patterns, unique wallets, darkweb dashboards, and trigger early alerts with a lightning-fast experience on our platform.
          </p>

          <div className="landing-hero-cta">
            <a href="/price-dashboard.html" className="landing-btn-outline with-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>
              View Dashboard
            </a>
            <a href="/tx-alert.html" className="landing-btn-orange">
              Start Scanning &gt;
            </a>
          </div>

          <div className="landing-hero-features">
            <div className="landing-feature">
              <div className="landing-feature-icon">⌘</div>
              <div className="landing-feature-text">
                <strong>Advanced Analytics</strong>
                <span>Detect peeling chains & mixing.</span>
              </div>
            </div>
            <div className="landing-feature">
              <div className="landing-feature-icon">⚡</div>
              <div className="landing-feature-text">
                <strong>Lightning-fast & Precise</strong>
                <span>Score transactions instantly.</span>
              </div>
            </div>
            <div className="landing-feature">
              <div className="landing-feature-icon">❖</div>
              <div className="landing-feature-text">
                <strong>Extensive Forensics API</strong>
                <span>Connect your intelligence pipeline.</span>
              </div>
            </div>
          </div>
        </div>

        <div className="landing-mockup-container">
          <img src="/dashboard_mockup.png" alt="Dashboard Mockup" className="landing-mockup-image" />
        </div>
      </div>

      <div className="landing-dark-section">
        <div className="landing-dark-content">
          <div className="landing-dark-header">
            <div className="landing-dark-badge">📊 Statistics</div>
            <h2>Realize how comprehensive<br/>TxIntel Security Platform is!</h2>
            <p>Here's a closer look at the numbers that define our intelligence system. See how we measure up!<br/><span className="landing-dark-muted">Constantly expanding 🚀</span></p>
          </div>

          <div className="landing-stats-grid">
            <div className="landing-stat">
              <div className="landing-stat-icon">⚄</div>
              <div className="landing-stat-title">Pattern Models</div>
              <div className="landing-stat-value">200+</div>
            </div>
            <div className="landing-stat">
              <div className="landing-stat-icon">⚄</div>
              <div className="landing-stat-title">Wallets Profiled</div>
              <div className="landing-stat-value">7.8M+</div>
            </div>
            <div className="landing-stat">
              <div className="landing-stat-icon">⚄</div>
              <div className="landing-stat-title">Threat Indicators</div>
              <div className="landing-stat-value">120K+</div>
            </div>
            <div className="landing-stat">
              <div className="landing-stat-icon">⚄</div>
              <div className="landing-stat-title">Rules & Heuristics</div>
              <div className="landing-stat-value">300+</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<MainPage />);
