import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Radar, ArrowRight, Gauge, MessageSquareWarning, ClipboardList, ShieldCheck,
  Search, PhoneCall, Menu, X, CheckCircle2,
} from "lucide-react";
import ThemeToggle from "../components/ThemeToggle";

/**
 * Public homepage. This is deliberately restrained: a public complaint
 * portal, not a SaaS marketing site. A first-time visitor should
 * understand what this system does within a few seconds - submit a
 * complaint, track it, get it resolved - without scrolling past fake
 * stats, testimonials, or feature marketing. Every claim below describes
 * real, current system functionality only.
 */
export default function LandingPage() {
  const [navOpen, setNavOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="landing">
      <header className={`landing-nav ${scrolled ? "is-scrolled" : ""}`}>
        <div className="landing-nav-inner">
          <a href="#top" className="landing-brand">
            <span className="sidebar-brand-mark"><Radar size={18} color="#fff" /></span>
            <span className="landing-brand-text">Dispatch</span>
          </a>

          <nav className="landing-nav-links">
            <a href="#top">Home</a>
            <a href="#about">About</a>
            <a href="#services">Services</a>
            <a href="#contact">Contact</a>
          </nav>

          <div className="landing-nav-actions">
            <ThemeToggle />
            <Link to="/login" className="btn-ghost">Login</Link>
            <Link to="/register" className="btn-primary">Register</Link>
          </div>

          <div className="landing-nav-mobile-actions">
            <ThemeToggle />
            <button className="landing-nav-burger" onClick={() => setNavOpen((v) => !v)} aria-label="Toggle menu">
              {navOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {navOpen && (
          <div className="landing-nav-mobile">
            <a href="#top" onClick={() => setNavOpen(false)}>Home</a>
            <a href="#about" onClick={() => setNavOpen(false)}>About</a>
            <a href="#services" onClick={() => setNavOpen(false)}>Services</a>
            <a href="#contact" onClick={() => setNavOpen(false)}>Contact</a>
            <Link to="/login" className="btn-ghost" onClick={() => setNavOpen(false)}>Login</Link>
            <Link to="/register" className="btn-primary" onClick={() => setNavOpen(false)}>Register</Link>
          </div>
        )}
      </header>

      <main id="top">
        {/* -------------------------------------------------------------- Hero */}
        <section className="landing-hero">
          <div className="landing-hero-copy">
            <h1>Complaint Management System</h1>
            <p className="landing-hero-sub">
              Submit, track and resolve complaints through one transparent platform.
            </p>
            <p className="landing-hero-sub" style={{ marginTop: "-18px" }}>
              Report an issue, follow its progress and receive updates until your complaint is resolved.
            </p>
            <div className="landing-hero-actions">
              <Link to="/register" className="btn-primary btn-lg">
                Submit a Complaint <ArrowRight size={16} />
              </Link>
              <Link to="/login" className="btn-secondary btn-lg">Track Complaint</Link>
            </div>
          </div>

          <div className="landing-hero-visual" aria-hidden="true">
            <ComplaintTrackMock />
          </div>
        </section>

        {/* --------------------------------------------------------- How we help */}
        <section id="services" className="landing-section">
          <div className="landing-section-head">
            <h2>How can we help you?</h2>
          </div>

          <div className="landing-feature-grid">
            <HelpCard icon={MessageSquareWarning} title="Submit a Complaint" color="#d1461f"
              text="Report an issue or complaint." to="/register" />
            <HelpCard icon={Search} title="Track Complaint" color="#2f5dff"
              text="Check the status of your complaint." to="/login" />
            <HelpCard icon={ClipboardList} title="Service Request" color="#12876b"
              text="Request a service or assistance." to="/register" />
            <HelpCard icon={PhoneCall} title="Contact Support" color="#b3760a"
              text="Get help with your issue." to="#contact" />
          </div>
        </section>

        {/* ------------------------------------------------------------ Workflow */}
        <section id="about" className="landing-workflow">
          <div className="landing-section-head">
            <h2>How It Works</h2>
          </div>

          <div className="landing-workflow-steps">
            <WorkflowStep n={1} title="Submit" text="Tell us about your issue." />
            <WorkflowStep n={2} title="Review" text="Your complaint is reviewed." />
            <WorkflowStep n={3} title="Assign" text="It is assigned to the appropriate team or agent." />
            <WorkflowStep n={4} title="Resolve" text="The issue is resolved and closed." />
          </div>
        </section>

        {/* -------------------------------------------------------- Accountability */}
        <section className="landing-section">
          <div className="landing-section-head">
            <h2>Every complaint deserves a response.</h2>
            <p>Your complaint is recorded, assigned to the responsible team and tracked through resolution.</p>
          </div>

          <div className="landing-role-grid">
            <RoleCard icon={ShieldCheck} title="Transparent" text="You can see exactly where your complaint stands, at every stage." />
            <RoleCard icon={Gauge} title="Accountable" text="Every complaint is assigned to a responsible team with a due date." />
            <RoleCard icon={CheckCircle2} title="Trackable" text="Follow your complaint from submission through to resolution." />
          </div>
        </section>

        {/* -------------------------------------------------------------- CTA band */}
        <section className="landing-cta" id="contact">
          <div className="landing-cta-inner">
            <div>
              <h2>Have an issue? Let us help.</h2>
              <p>Create an account and submit your complaint in minutes.</p>
            </div>
            <Link to="/register" className="btn-primary btn-lg">
              Submit a Complaint <ArrowRight size={16} />
            </Link>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <div className="landing-brand">
            <span className="sidebar-brand-mark"><Radar size={16} color="#fff" /></span>
            <span className="landing-brand-text">Dispatch</span>
          </div>
          <span className="landing-footer-tag">COMPLAINT MANAGEMENT SYSTEM</span>
          <div className="landing-footer-links">
            <Link to="/login">Login</Link>
            <Link to="/register">Register</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

function HelpCard({ icon: Icon, title, text, color, to }: { icon: any; title: string; text: string; color: string; to: string }) {
  return (
    <Link to={to} className="landing-feature-card" style={{ textDecoration: "none" }}>
      <span className="landing-feature-icon" style={{ background: `${color}17`, color }}>
        <Icon size={19} />
      </span>
      <h3>{title}</h3>
      <p>{text}</p>
    </Link>
  );
}

function WorkflowStep({ n, title, text }: { n: number; title: string; text: string }) {
  return (
    <div className="landing-workflow-step">
      <span className="landing-workflow-num">{String(n).padStart(2, "0")}</span>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function RoleCard({ icon: Icon, title, text }: { icon: any; title: string; text: string }) {
  return (
    <div className="landing-role-card">
      <Icon size={18} style={{ color: "var(--brand)", marginBottom: 8 }} />
      <h4>{title}</h4>
      <p>{text}</p>
    </div>
  );
}

/**
 * A single, simple complaint-tracking visual for the hero - not a
 * complicated dashboard mockup. Illustrative example data only.
 */
function ComplaintTrackMock() {
  const steps = ["Submitted", "Reviewed", "Assigned", "Resolved"];
  const activeIndex = 2;
  return (
    <div className="ticket-mock">
      <div className="ticket-mock-topbar">
        <div className="ticket-mock-dots"><span /><span /><span /></div>
        <div className="ticket-mock-search" />
      </div>
      <div className="ticket-mock-body">
        <div className="ticket-mock-head">
          <div>
            <div className="ticket-mock-ref">Complaint ID</div>
            <div className="ticket-mock-title">CMP-2031</div>
          </div>
          <span className="status-badge" style={{ backgroundColor: "#2f5dff17", color: "#2f5dff" }}>In Progress</span>
        </div>

        <div className="ticket-mock-steps">
          {steps.map((step, i) => (
            <div key={step} className={`ticket-mock-step${i <= activeIndex ? " done" : ""}${i === activeIndex ? " current" : ""}`}>
              <span className="ticket-mock-step-dot">{i <= activeIndex && <CheckCircle2 size={10} />}</span>
              <span className="ticket-mock-step-label">{step}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
