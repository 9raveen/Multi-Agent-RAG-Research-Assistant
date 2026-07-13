import React from "react";
import ThemeToggle from "./ThemeToggle";
import "./CoverPage.css";

const TICKER_ITEMS = [
  "ISSUE 07",
  "MULTI-AGENT RETRIEVAL",
  "CITED ANSWERS",
  "PRIVATE DOCUMENTS",
  "RESEARCH, DISTILLED",
  new Date()
    .toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    })
    .toUpperCase(),
  "VOL. 01",
];

export default function CoverPage({ onEnterWorkspace, theme, onToggleTheme }) {
  const tickerText = TICKER_ITEMS.join(" \u00B7 ") + " \u00B7 ";

  return (
    <div className="cover-page">
      <nav className="cover-nav">
        <div className="cover-logo">
          <img src="/logo.png" alt="m logo" className="custom-logo" /> MARA / AI
        </div>
        <div className="cover-links">
          <a href="#agents">AGENTS</a>
          <a href="#workflow">WORKFLOW</a>
          <a href="#manifesto">MANIFESTO</a>
        </div>
        <div className="cover-nav-actions">
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
          <button className="cover-btn-dark" onClick={onEnterWorkspace}>
            Enter workspace &rarr;
          </button>
        </div>
      </nav>

      <div className="cover-ticker">
        <div className="ticker-track">
          {[0, 1, 2, 3].map((i) => (
            <span key={i}>{tickerText}</span>
          ))}
        </div>
      </div>

      <main className="cover-main">
        <section className="hero-section">
          <div className="hero-content">
            <span className="section-label">
              A RESEARCH ATELIER FOR THE LLM ERA
            </span>
            <h1 className="hero-title">
              Read <span className="italic-serif">everything.</span>
              <br />
              Answer <span className="italic-serif underline">anything.</span>
            </h1>
            <p className="hero-description">
              MARA is a multi-agent RAG assistant. It coordinates specialised
              researchers to read your library, weigh sources, and hand you a
              citable answer — not a guess.
            </p>
            <div className="hero-actions">
              <button
                className="cover-btn-dark large"
                onClick={onEnterWorkspace}
              >
                Start researching &rarr;
              </button>
              <button className="cover-link-btn" onClick={onEnterWorkspace}>
                OR SIGN IN &rarr;
              </button>
            </div>
          </div>
          <div className="hero-illustration">
            <div className="illustration-placeholder">
              <img
                src="/reading-room.png"
                alt="The Reading Room"
                className="reading-room-img"
              />
              <div className="illustration-caption">
                <span>FIG. 01</span>
                <span>THE READING ROOM</span>
              </div>
            </div>
          </div>
        </section>

        <section id="agents" className="features-section">
          <div className="feature-card">
            <span className="feature-label">AGENT 01</span>
            <div className="feature-icon">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
            </div>
            <h3 className="feature-title">The Archivist</h3>
            <p className="feature-desc">
              Indexes your uploads. Chunks, embeds, remembers.
            </p>
          </div>
          <div className="feature-card border-left border-right">
            <span className="feature-label">AGENT 02</span>
            <div className="feature-icon">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <rect x="14" y="14" width="4" height="4" />
                <rect x="6" y="14" width="4" height="4" />
                <rect x="10" y="6" width="4" height="4" />
                <path d="M12 10v4" />
                <path d="M8 14v-2h8v2" />
              </svg>
            </div>
            <h3 className="feature-title">The Analyst</h3>
            <p className="feature-desc">
              Traverses sources, weighs evidence, forms a thesis.
            </p>
          </div>
          <div className="feature-card">
            <span className="feature-label">AGENT 03</span>
            <div className="feature-icon">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                <path d="M13 8H7" />
                <path d="M17 12H7" />
              </svg>
            </div>
            <h3 className="feature-title">The Editor</h3>
            <p className="feature-desc">
              Writes the answer in your voice — with citations.
            </p>
          </div>
        </section>

        <section id="workflow" className="workflow-section">
          <div className="workflow-header">
            <span className="section-label">&sect; 02 - THE WORKFLOW</span>
            <h2 className="workflow-title">
              A quiet workspace for loud
              <br />
              questions.
            </h2>
          </div>
          <div className="workflow-grid">
            <div className="workflow-step">
              <div className="step-number">01</div>
              <h4 className="step-title">Upload</h4>
              <p className="step-desc">
                Drop in PDFs, notes, papers. MARA reads them the moment they
                land.
              </p>
            </div>
            <div className="workflow-step">
              <div className="step-number">02</div>
              <h4 className="step-title">Ask</h4>
              <p className="step-desc">
                Type in plain English. The agents plan, retrieve, and reason
                together.
              </p>
            </div>
            <div className="workflow-step">
              <div className="step-number">03</div>
              <h4 className="step-title">Cite</h4>
              <p className="step-desc">
                Every claim can be traced. Your library becomes a searchable
                mind.
              </p>
            </div>
          </div>
        </section>

        <section id="manifesto" className="manifesto-section">
          <span className="section-label manifesto-label">
            &sect; 03 - MANIFESTO
          </span>
          <div className="manifesto-content">
            <h2 className="manifesto-quote">
              “Knowledge shouldn't feel like a slot machine.
              <br />
              <span style={{ color: "#D93025" }}>
                We built MARA so answers come with a paper
                <br />
                trail &mdash; the difference between an oracle and a<br />
                colleague.”
              </span>
            </h2>
            <div className="manifesto-author">
              <span className="author-star">✧</span> THE MARA COLLECTIVE
            </div>
          </div>
        </section>
      </main>

      <footer className="cover-footer">
        <div className="footer-left">
          &copy; 2026 MARA AI &middot; STOCKHOLM &harr; EVERYWHERE
        </div>
        <div className="footer-right">
          <button className="cover-link-btn" onClick={onEnterWorkspace}>
            ENTER WORKSPACE &rarr;
          </button>
        </div>
      </footer>
    </div>
  );
}
