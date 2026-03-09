"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Brain,
  CheckCircle2,
  ChevronRight,
  FileBarChart,
  FileSearch,
  Globe,
  Link2,
  Lock,
  Menu,
  PieChart,
  Search,
  Shield,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  X,
  Zap,
} from "lucide-react";

// ── Hooks ─────────────────────────────────────────────────────────────────────

function useScrolled(threshold = 24) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > threshold);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, [threshold]);
  return scrolled;
}

function useFadeIn(threshold = 0.1) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) { setVisible(true); observer.disconnect(); }
      },
      { threshold }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);
  return { ref, visible };
}

function FadeIn({ children, delay = 0, className = "" }: {
  children: React.ReactNode; delay?: number; className?: string;
}) {
  const { ref, visible } = useFadeIn();
  return (
    <div ref={ref} className={className} style={{
      opacity: visible ? 1 : 0,
      transform: visible ? "translateY(0)" : "translateY(18px)",
      transition: `opacity 0.6s ease ${delay}ms, transform 0.6s ease ${delay}ms`,
    }}>
      {children}
    </div>
  );
}

// ── Static data ───────────────────────────────────────────────────────────────

const GOLD = "#c9a84c";

const TRUST_STATS = [
  { value: "81", label: "Application Modules" },
  { value: "78", label: "AI Task Types" },
  { value: "25", label: "Automated Workflows" },
  { value: "176", label: "Data Models" },
];

const PROJECT_HOLDER_ITEMS = [
  "Know if your project is investment-ready",
  "Generate professional documentation and reports",
  "Source funding and connect with matched investors",
  "Track readiness with AI-powered Signal Score",
];

const INVESTOR_ITEMS = [
  "Source and screen deals with AI intelligence",
  "Monitor portfolio performance in real-time",
  "Automate LP reporting and compliance",
  "Benchmark against peer groups instantly",
];

const FEATURES = [
  {
    Icon: Target,
    title: "Deal Sourcing & Screening",
    desc: "AI-powered Signal Score rates projects across 6 dimensions and 48 criteria",
  },
  {
    Icon: FileSearch,
    title: "Due Diligence & Documents",
    desc: "Automated document classification, extraction, and secure virtual data room",
  },
  {
    Icon: Brain,
    title: "AI-Powered Analysis",
    desc: "Ralph AI assistant with 19 specialized tools across the platform for deep analysis",
  },
  {
    Icon: BarChart3,
    title: "Portfolio Management",
    desc: "Real-time covenant monitoring, benchmarks, and cashflow pacing with daily snapshots",
  },
  {
    Icon: FileBarChart,
    title: "Automated Reporting",
    desc: "LP quarterly reports in PDF, Excel, and PowerPoint — reducing reporting from weeks to hours",
  },
  {
    Icon: ShieldCheck,
    title: "Compliance & Risk",
    desc: "Full audit trail, source citations, data lineage, and GDPR-compliant architecture",
  },
];

const PERSONAS = [
  { Icon: TrendingUp, role: "Project Holders & Developers", desc: "Signal Score, funding readiness, investor matching" },
  { Icon: PieChart,   role: "Fund Managers & GPs",          desc: "Portfolio oversight, LP reporting, benchmark positioning" },
  { Icon: Search,     role: "Deal Teams & Analysts",         desc: "AI screening, document processing, due diligence automation" },
  { Icon: BarChart3,  role: "Portfolio Managers",            desc: "Covenant monitoring, KPI tracking, pacing models" },
  { Icon: Users,      role: "Limited Partners",              desc: "Real-time portal, structured Q&A, engagement analytics" },
  { Icon: Shield,     role: "Compliance Officers",           desc: "Audit trails, AI citations, data lineage, redaction" },
];

const SECURITY_BADGES = [
  { Icon: Globe,       label: "EU-Hosted" },
  { Icon: Shield,      label: "GDPR Compliant" },
  { Icon: CheckCircle2,label: "SOC 2-Ready" },
  { Icon: Lock,        label: "AES-256 Encryption" },
  { Icon: Zap,         label: "TLS 1.3" },
  { Icon: Link2,       label: "Blockchain Audit Trail" },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function HomePage() {
  const scrolled = useScrolled();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white font-sans antialiased">

      {/* ── Navbar ── */}
      <header className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled ? "bg-white/96 shadow-sm backdrop-blur-md" : "bg-transparent"
      }`}>
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <div className={`flex h-7 w-7 items-center justify-center rounded-md text-xs font-bold text-white transition-colors duration-300 ${
              scrolled ? "bg-[#1a2332]" : "bg-white/15 backdrop-blur-sm"
            }`}>S</div>
            <span className={`text-sm font-bold tracking-wide transition-colors duration-300 ${
              scrolled ? "text-[#1a2332]" : "text-white"
            }`}>SCR Platform</span>
          </Link>

          <nav className="hidden items-center gap-8 md:flex">
            {["Platform", "Features", "Security", "Contact"].map((item) => (
              <a key={item} href={`#${item.toLowerCase()}`}
                className={`text-sm font-medium transition-colors duration-300 hover:opacity-70 ${
                  scrolled ? "text-neutral-600" : "text-white/80"
                }`}>
                {item}
              </a>
            ))}
          </nav>

          <div className="hidden items-center gap-3 md:flex">
            <Link href="/sign-in" className={`rounded-lg px-4 py-2 text-sm font-medium transition-all duration-300 ${
              scrolled
                ? "border border-neutral-300 text-neutral-700 hover:border-neutral-400 hover:bg-neutral-50"
                : "border border-white/30 text-white hover:bg-white/10"
            }`}>Sign In</Link>
            <Link href="/sign-in" className={`rounded-lg px-4 py-2 text-sm font-medium transition-all duration-300 ${
              scrolled
                ? "bg-[#1a2332] text-white hover:bg-[#243049]"
                : "bg-white text-[#1a2332] hover:bg-white/90"
            }`}>Get Started</Link>
          </div>

          <button className={`md:hidden transition-colors ${scrolled ? "text-neutral-700" : "text-white"}`}
            onClick={() => setMobileOpen((v) => !v)} aria-label="Toggle menu">
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {mobileOpen && (
          <div className="border-t border-white/10 bg-[#1a2332] px-6 py-4 md:hidden">
            <nav className="flex flex-col gap-4">
              {["Platform", "Features", "Security", "Contact"].map((item) => (
                <a key={item} href={`#${item.toLowerCase()}`}
                  className="text-sm font-medium text-white/80"
                  onClick={() => setMobileOpen(false)}>{item}</a>
              ))}
              <div className="mt-2 flex flex-col gap-2 border-t border-white/10 pt-4">
                <Link href="/sign-in" className="rounded-lg border border-white/30 px-4 py-2 text-center text-sm font-medium text-white">Sign In</Link>
                <Link href="/sign-in" className="rounded-lg bg-white px-4 py-2 text-center text-sm font-medium text-[#1a2332]">Get Started</Link>
              </div>
            </nav>
          </div>
        )}
      </header>

      {/* ── Hero ── */}
      <section className="relative flex min-h-[92vh] items-center justify-center overflow-hidden bg-[#1a2332]" id="platform">
        {/* Grid pattern */}
        <div className="absolute inset-0 opacity-[0.035]" style={{
          backgroundImage: "linear-gradient(rgba(255,255,255,0.5) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.5) 1px,transparent 1px)",
          backgroundSize: "56px 56px",
        }} />
        {/* Subtle radial glow */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_35%,rgba(201,168,76,0.08),transparent_60%)]" />
        <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[#1a2332] to-transparent" />

        <div className="relative mx-auto max-w-4xl px-6 py-28 text-center lg:px-8"
          style={{ animation: "heroFadeIn 0.85s ease both" }}>
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-[11px] font-medium tracking-widest text-white/50 uppercase">
            <Sparkles className="h-3 w-3" style={{ color: GOLD }} />
            AI-Native Investment Platform
          </div>

          <h1 className="text-4xl font-bold leading-[1.1] tracking-tight text-white sm:text-5xl lg:text-[3.5rem]">
            The AI-Native Operating System{" "}
            <span className="text-white/65">for Sustainable Infrastructure Investment</span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-white/50 sm:text-lg">
            One platform for the entire investment lifecycle — whether you&apos;re sourcing deals or
            raising capital. SCR Platform unifies deal sourcing, due diligence, portfolio monitoring,
            LP reporting, and compliance into a single intelligent operating system.
          </p>

          <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Link href="/sign-in"
              className="inline-flex items-center gap-2 rounded-xl px-8 py-3.5 text-sm font-semibold text-[#1a2332] transition-all hover:shadow-lg"
              style={{ backgroundColor: GOLD }}>
              Get Started <ArrowRight className="h-4 w-4" />
            </Link>
            <a href="mailto:contact@pampgroup.com"
              className="inline-flex items-center gap-2 rounded-xl border px-8 py-3.5 text-sm font-semibold text-white transition-all hover:bg-white/5"
              style={{ borderColor: "rgba(201,168,76,0.4)" }}>
              Book a Demo <ChevronRight className="h-4 w-4" />
            </a>
          </div>
        </div>

        <style>{`
          @keyframes heroFadeIn {
            from { opacity:0; transform:translateY(24px); }
            to   { opacity:1; transform:translateY(0); }
          }
        `}</style>
      </section>

      {/* ── Trust Bar ── */}
      <section className="bg-[#1a2332]">
        {/* Gold top line */}
        <div className="h-px w-full" style={{ background: `linear-gradient(90deg, transparent, ${GOLD}, transparent)` }} />
        <div className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            {TRUST_STATS.map(({ value, label }) => (
              <div key={label} className="flex flex-col items-center text-center">
                <span className="text-4xl font-bold tabular-nums" style={{ color: GOLD }}>{value}</span>
                <span className="mt-1 text-xs font-medium tracking-wide text-white/45 uppercase">{label}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="h-px w-full" style={{ background: `linear-gradient(90deg, transparent, ${GOLD}, transparent)` }} />
      </section>

      {/* ── Value Proposition ── */}
      <section className="bg-white py-16">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <FadeIn className="mx-auto max-w-2xl text-center">
            <h2 className="text-2xl font-bold tracking-tight text-[#1a2332] sm:text-3xl">
              Everything You Need. One Platform.
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-neutral-500 sm:text-base">
              Stop juggling 4–5 disconnected tools. SCR Platform replaces your fragmented workflow
              with a single, intelligent system.
            </p>
          </FadeIn>

          <FadeIn delay={100} className="mt-10">
            <div className="grid gap-0 overflow-hidden rounded-2xl border border-neutral-100 shadow-sm sm:grid-cols-2">
              {/* Left — Project Holders */}
              <div className="border-b border-neutral-100 bg-neutral-50 p-8 sm:border-b-0 sm:border-r-0">
                <div className="mb-1 text-[10px] font-semibold tracking-widest uppercase" style={{ color: GOLD }}>
                  For Project Holders &amp; Developers
                </div>
                <ul className="mt-4 space-y-3">
                  {PROJECT_HOLDER_ITEMS.map((item) => (
                    <li key={item} className="flex items-start gap-2.5 text-sm text-neutral-700">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" style={{ color: GOLD }} />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Gold divider (desktop: vertical) */}
              <div className="hidden sm:block" style={{
                borderLeft: `1px solid ${GOLD}`,
                opacity: 0.35,
              }} />

              {/* Right — Investors */}
              <div className="bg-[#1a2332] p-8">
                <div className="mb-1 text-[10px] font-semibold tracking-widest uppercase" style={{ color: GOLD }}>
                  For Investors &amp; Fund Managers
                </div>
                <ul className="mt-4 space-y-3">
                  {INVESTOR_ITEMS.map((item) => (
                    <li key={item} className="flex items-start gap-2.5 text-sm text-white/75">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" style={{ color: GOLD }} />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── Platform Overview ── */}
      <section id="features" className="bg-neutral-50 py-16">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <FadeIn className="mx-auto max-w-2xl text-center">
            <h2 className="text-2xl font-bold tracking-tight text-[#1a2332] sm:text-3xl">
              Built for the Full Investment Lifecycle
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-neutral-500 sm:text-base">
              From first project screen through ongoing portfolio management and final investor
              reporting — every stage unified on a single platform backed by enterprise AI.
            </p>
          </FadeIn>

          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ Icon, title, desc }, i) => (
              <FadeIn key={title} delay={i * 60}>
                <div className="group flex flex-col gap-3 rounded-xl border border-neutral-200 bg-white p-6 transition-all duration-200 hover:border-[#c9a84c]/40 hover:shadow-md">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#1a2332]/5 transition-colors group-hover:bg-[#1a2332]/8">
                    <Icon className="h-5 w-5 text-[#1a2332] transition-colors group-hover:text-[#c9a84c]" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-900">{title}</h3>
                    <p className="mt-1 text-xs leading-relaxed text-neutral-500">{desc}</p>
                  </div>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── Who It's For ── */}
      <section className="bg-white py-16">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <FadeIn className="mx-auto max-w-xl text-center">
            <h2 className="text-2xl font-bold tracking-tight text-[#1a2332] sm:text-3xl">
              Purpose-Built for Every Role
            </h2>
            <p className="mt-3 text-sm text-neutral-500">
              One platform, six distinct experiences — serving both sides of the market.
            </p>
          </FadeIn>

          <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {PERSONAS.map(({ Icon, role, desc }, i) => (
              <FadeIn key={role} delay={i * 50}>
                <div className="flex items-start gap-3.5 rounded-xl border border-neutral-100 bg-neutral-50 p-5 transition-all duration-200 hover:border-[#c9a84c]/30 hover:bg-white hover:shadow-sm">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#1a2332]/6">
                    <Icon className="h-4 w-4 text-[#1a2332]" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-neutral-900">{role}</p>
                    <p className="mt-0.5 text-xs text-neutral-500">{desc}</p>
                  </div>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── Security strip ── */}
      <section id="security" className="bg-[#1a2332] py-10">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <FadeIn className="text-center">
            <p className="text-[10px] font-semibold tracking-widest uppercase" style={{ color: GOLD }}>
              Enterprise-Grade Security
            </p>
          </FadeIn>
          <FadeIn delay={80} className="mt-6">
            <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4">
              {SECURITY_BADGES.map(({ Icon, label }) => (
                <div key={label}
                  className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-white/70">
                  <Icon className="h-3.5 w-3.5" style={{ color: GOLD }} />
                  {label}
                </div>
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="relative overflow-hidden bg-[#1a2332] py-20">
        {/* Gold accent line top */}
        <div className="absolute inset-x-0 top-0 h-px" style={{ background: `linear-gradient(90deg, transparent, ${GOLD}, transparent)` }} />
        {/* Subtle gold glow */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(201,168,76,0.07),transparent_55%)]" />

        <div className="relative mx-auto max-w-2xl px-6 text-center lg:px-8">
          <FadeIn>
            <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl lg:text-4xl">
              Ready to Transform Your Investment Operations?
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-sm leading-relaxed text-white/50 sm:text-base">
              Whether you&apos;re raising capital or deploying it — SCR Platform gives you the
              intelligence to move faster and with confidence.
            </p>
            <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
              <Link href="/sign-in"
                className="inline-flex items-center gap-2 rounded-xl px-8 py-3.5 text-sm font-semibold text-[#1a2332] transition-all hover:opacity-90 hover:shadow-lg"
                style={{ backgroundColor: GOLD }}>
                Get Started <ArrowRight className="h-4 w-4" />
              </Link>
              <a href="mailto:contact@pampgroup.com"
                className="inline-flex items-center gap-2 rounded-xl border border-white/20 px-8 py-3.5 text-sm font-semibold text-white transition-all hover:border-white/35 hover:bg-white/5">
                Book a Demo <ChevronRight className="h-4 w-4" />
              </a>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer id="contact" className="bg-[#0f1620] py-10">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
            <div className="flex items-center gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-white/10 text-xs font-bold text-white">S</div>
              <span className="text-sm font-bold tracking-wide text-white">SCR Platform</span>
            </div>
            <nav className="flex flex-wrap gap-5">
              {["Platform", "Features", "Security", "Legal", "Privacy Policy"].map((item) => (
                <a key={item} href="#"
                  className="text-xs font-medium text-white/35 transition-colors hover:text-white/65">
                  {item}
                </a>
              ))}
            </nav>
          </div>
          <div className="mt-8 flex flex-col items-start justify-between gap-2 border-t border-white/6 pt-6 sm:flex-row sm:items-center">
            <p className="text-xs text-white/25">© 2026 SCR Platform. All rights reserved.</p>
            <p className="text-xs text-white/20">EU-hosted · GDPR-compliant.</p>
          </div>
        </div>
      </footer>

    </div>
  );
}
