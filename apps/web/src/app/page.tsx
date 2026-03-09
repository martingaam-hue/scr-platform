"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Brain,
  CheckCircle2,
  ChevronRight,
  Clock,
  Code2,
  Database,
  FileBarChart,
  FileSearch,
  FileText,
  Globe,
  Layers,
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

// ── Scroll hooks ──────────────────────────────────────────────────────────────

function useScrolled(threshold = 24) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > threshold);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, [threshold]);
  return scrolled;
}

function useFadeIn(threshold = 0.12) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);
  return { ref, visible };
}

function FadeIn({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const { ref, visible } = useFadeIn();
  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(22px)",
        transition: `opacity 0.65s ease ${delay}ms, transform 0.65s ease ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

// ── Static data ───────────────────────────────────────────────────────────────

const TRUST_STATS = [
  { value: "81", label: "Application Modules" },
  { value: "5", label: "AI Providers" },
  { value: "78", label: "AI Task Types" },
  { value: "25", label: "Automated Workflows" },
  { value: "176", label: "Data Models" },
];

const FEATURES = [
  {
    Icon: Target,
    title: "Deal Sourcing & Screening",
    desc: "AI-powered Signal Score rates every project across 6 dimensions and 48 criteria",
  },
  {
    Icon: FileSearch,
    title: "Due Diligence & Documents",
    desc: "Automated document classification, extraction, and virtual data room with engagement analytics",
  },
  {
    Icon: Brain,
    title: "Investment Analysis & AI",
    desc: "Ralph AI assistant with 19 specialized tools across 5 AI providers for deep investment analysis",
  },
  {
    Icon: BarChart3,
    title: "Portfolio Management",
    desc: "Real-time covenant monitoring, benchmark comparison, and cashflow pacing with daily metric snapshots",
  },
  {
    Icon: FileBarChart,
    title: "LP Reporting",
    desc: "Automated quarterly reports in PDF, Excel, and PowerPoint — reducing reporting from weeks to hours",
  },
  {
    Icon: ShieldCheck,
    title: "Compliance & Risk",
    desc: "Full audit trail, AI source citations, data lineage, and GDPR-compliant infrastructure",
  },
];

const AI_PROVIDERS = [
  { name: "Anthropic", model: "Claude", abbr: "AN" },
  { name: "OpenAI", model: "GPT-4o", abbr: "OA" },
  { name: "Google", model: "Gemini", abbr: "GG" },
  { name: "xAI", model: "Grok", abbr: "xA" },
  { name: "DeepSeek", model: "DeepSeek", abbr: "DS" },
];

const PERSONAS = [
  {
    Icon: TrendingUp,
    role: "Fund Managers & GPs",
    desc: "Unified dashboard, Signal Score, automated LP reports, benchmark positioning",
  },
  {
    Icon: Search,
    role: "Deal Teams & Analysts",
    desc: "AI screening, Smart Screener, document processing, due diligence automation",
  },
  {
    Icon: PieChart,
    role: "Portfolio Managers",
    desc: "Covenant monitoring, KPI tracking, trend analysis, pacing models",
  },
  {
    Icon: Users,
    role: "Limited Partners",
    desc: "Real-time portal, benchmark context, structured Q&A, engagement tracking",
  },
  {
    Icon: FileText,
    role: "Compliance Officers",
    desc: "Audit trails, source citations, data lineage, AI-powered redaction",
  },
  {
    Icon: Code2,
    role: "External Integrators",
    desc: "White-label, custom domains, CRM sync, webhooks, REST API",
  },
];

const SECURITY_ITEMS = [
  { Icon: Globe, label: "EU-Hosted", sub: "AWS eu-west-1" },
  { Icon: Shield, label: "GDPR Compliant", sub: "Full compliance" },
  { Icon: CheckCircle2, label: "SOC 2 Ready", sub: "Type II" },
  { Icon: Lock, label: "AES-256 Encrypted", sub: "At rest" },
  { Icon: Zap, label: "TLS 1.3", sub: "In transit" },
  { Icon: Layers, label: "Multi-AZ", sub: "High availability" },
  { Icon: Clock, label: "< 1 Hour RPO", sub: "Recovery objective" },
  { Icon: Link2, label: "Blockchain Audit", sub: "Immutable trail" },
  { Icon: ShieldCheck, label: "WAF Protection", sub: "Web application" },
  { Icon: Database, label: "RBAC", sub: "4 permission levels" },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function HomePage() {
  const scrolled = useScrolled();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white font-sans antialiased">

      {/* ── Navbar ── */}
      <header
        className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
          scrolled
            ? "bg-white/95 shadow-sm backdrop-blur-md"
            : "bg-transparent"
        }`}
      >
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-8">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5">
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-md text-xs font-bold text-white transition-colors duration-300 ${
                scrolled ? "bg-[#1a2332]" : "bg-white/20 backdrop-blur-sm"
              }`}
            >
              S
            </div>
            <span
              className={`text-sm font-bold tracking-wide transition-colors duration-300 ${
                scrolled ? "text-[#1a2332]" : "text-white"
              }`}
            >
              SCR Platform
            </span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden items-center gap-8 md:flex">
            {["Platform", "Features", "Security", "Contact"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className={`text-sm font-medium transition-colors duration-300 hover:opacity-70 ${
                  scrolled ? "text-neutral-600" : "text-white/80"
                }`}
              >
                {item}
              </a>
            ))}
          </nav>

          {/* Desktop CTAs */}
          <div className="hidden items-center gap-3 md:flex">
            <Link
              href="/sign-in"
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-all duration-300 ${
                scrolled
                  ? "border border-neutral-300 text-neutral-700 hover:border-neutral-400 hover:bg-neutral-50"
                  : "border border-white/30 text-white hover:bg-white/10"
              }`}
            >
              Sign In
            </Link>
            <Link
              href="/sign-in"
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-all duration-300 ${
                scrolled
                  ? "bg-[#1a2332] text-white hover:bg-[#243049]"
                  : "bg-white text-[#1a2332] hover:bg-white/90"
              }`}
            >
              Get Started
            </Link>
          </div>

          {/* Mobile menu toggle */}
          <button
            className={`md:hidden transition-colors ${
              scrolled ? "text-neutral-700" : "text-white"
            }`}
            onClick={() => setMobileOpen((v) => !v)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {/* Mobile menu */}
        {mobileOpen && (
          <div className="border-t border-white/10 bg-[#1a2332] px-6 py-4 md:hidden">
            <nav className="flex flex-col gap-4">
              {["Platform", "Features", "Security", "Contact"].map((item) => (
                <a
                  key={item}
                  href={`#${item.toLowerCase()}`}
                  className="text-sm font-medium text-white/80"
                  onClick={() => setMobileOpen(false)}
                >
                  {item}
                </a>
              ))}
              <div className="mt-2 flex flex-col gap-2 border-t border-white/10 pt-4">
                <Link
                  href="/sign-in"
                  className="rounded-lg border border-white/30 px-4 py-2 text-center text-sm font-medium text-white"
                >
                  Sign In
                </Link>
                <Link
                  href="/sign-in"
                  className="rounded-lg bg-white px-4 py-2 text-center text-sm font-medium text-[#1a2332]"
                >
                  Get Started
                </Link>
              </div>
            </nav>
          </div>
        )}
      </header>

      {/* ── Hero ── */}
      <section className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#1a2332]">
        {/* Geometric grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.4) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />
        {/* Radial glow */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_40%,rgba(37,99,235,0.12),transparent_65%)]" />
        {/* Bottom fade */}
        <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-[#1a2332] to-transparent" />

        <div className="relative mx-auto max-w-4xl px-6 py-32 text-center lg:px-8">
          <div
            style={{
              opacity: 1,
              animation: "heroFadeIn 0.9s ease both",
            }}
          >
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium tracking-widest text-white/60 uppercase">
              <Sparkles className="h-3 w-3" />
              AI-Native Investment Platform
            </div>

            <h1 className="text-4xl font-bold leading-[1.1] tracking-tight text-white sm:text-5xl lg:text-6xl xl:text-7xl">
              The AI-Native Operating System{" "}
              <span className="text-white/70">for Sustainable Infrastructure Investment</span>
            </h1>

            <p className="mx-auto mt-8 max-w-2xl text-lg leading-relaxed text-white/55">
              Unifying deal sourcing, due diligence, portfolio monitoring, LP reporting, and
              regulatory compliance into a single intelligent platform — purpose-built for fund
              managers, asset developers, and institutional investors.
            </p>

            <div className="mt-12 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Link
                href="/sign-in"
                className="inline-flex items-center gap-2 rounded-xl bg-white px-8 py-3.5 text-sm font-semibold text-[#1a2332] transition-all hover:bg-white/90 hover:shadow-lg"
              >
                Get Started
                <ArrowRight className="h-4 w-4" />
              </Link>
              <a
                href="mailto:contact@pampgroup.com"
                className="inline-flex items-center gap-2 rounded-xl border border-white/25 px-8 py-3.5 text-sm font-semibold text-white transition-all hover:border-white/40 hover:bg-white/5"
              >
                Book a Demo
                <ChevronRight className="h-4 w-4" />
              </a>
            </div>
          </div>
        </div>

        <style>{`
          @keyframes heroFadeIn {
            from { opacity: 0; transform: translateY(28px); }
            to   { opacity: 1; transform: translateY(0); }
          }
        `}</style>
      </section>

      {/* ── Trust Bar ── */}
      <section className="border-y border-neutral-100 bg-neutral-50" id="platform">
        <div className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
          <div className="flex flex-wrap items-center justify-center gap-8 sm:gap-0 sm:divide-x sm:divide-neutral-200">
            {TRUST_STATS.map(({ value, label }) => (
              <div key={label} className="flex flex-col items-center px-8 text-center">
                <span className="text-2xl font-bold tabular-nums text-[#1a2332]">{value}</span>
                <span className="mt-0.5 text-xs font-medium tracking-wide text-neutral-400 uppercase">
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Platform Overview ── */}
      <section id="features" className="py-28">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <FadeIn className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-[#1a2332] sm:text-4xl">
              Built for the Full Investment Lifecycle
            </h2>
            <p className="mt-5 text-base leading-relaxed text-neutral-500">
              From the first project screen through ongoing portfolio management and final investor
              reporting — SCR Platform eliminates fragmentation by unifying every stage on a single
              platform backed by enterprise-grade AI.
            </p>
          </FadeIn>

          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ Icon, title, desc }, i) => (
              <FadeIn key={title} delay={i * 70}>
                <div className="group relative flex flex-col gap-4 rounded-2xl border border-neutral-100 bg-white p-7 shadow-sm transition-all duration-300 hover:border-neutral-200 hover:shadow-md">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#1a2332]/6">
                    <Icon className="h-5 w-5 text-[#1a2332]" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-neutral-900">{title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-neutral-500">{desc}</p>
                  </div>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── AI Section ── */}
      <section className="bg-[#1a2332] py-28">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <FadeIn className="mx-auto max-w-2xl text-center">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium tracking-widest text-white/50 uppercase">
              <Sparkles className="h-3 w-3" />
              Multi-Provider AI
            </div>
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Intelligence at Every Layer
            </h2>
            <p className="mt-5 text-base leading-relaxed text-white/55">
              AI is not an add-on. It&apos;s woven into every workflow — from the first document
              classification when a file is uploaded to nightly benchmark comparisons and
              personalised investment briefings.
            </p>
          </FadeIn>

          <FadeIn delay={150} className="mt-14">
            <div className="flex flex-wrap items-center justify-center gap-4">
              {AI_PROVIDERS.map(({ name, model, abbr }) => (
                <div
                  key={name}
                  className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-6 py-4 backdrop-blur-sm"
                >
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/10 text-xs font-bold text-white">
                    {abbr}
                  </div>
                  <div>
                    <p className="text-[11px] font-medium tracking-wide text-white/45 uppercase">
                      {name}
                    </p>
                    <p className="text-sm font-semibold text-white">{model}</p>
                  </div>
                </div>
              ))}
            </div>
          </FadeIn>

          <FadeIn delay={250} className="mt-10 text-center">
            <p className="text-sm text-white/40">
              78 distinct AI task types, each routed to the optimal provider.{" "}
              <span className="text-white/60">
                Automatic fallback ensures uninterrupted capability.
              </span>
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ── Who It's For ── */}
      <section className="py-28">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <FadeIn className="mx-auto max-w-xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-[#1a2332] sm:text-4xl">
              Purpose-Built for Every Role
            </h2>
            <p className="mt-4 text-base text-neutral-500">
              One platform, six distinct user experiences — each tuned to the needs of the role.
            </p>
          </FadeIn>

          <div className="mt-16 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {PERSONAS.map(({ Icon, role, desc }, i) => (
              <FadeIn key={role} delay={i * 60}>
                <div className="flex flex-col gap-3 rounded-2xl bg-neutral-50 p-7 transition-all duration-300 hover:bg-neutral-100/70">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#1a2332]/8">
                    <Icon className="h-5 w-5 text-[#1a2332]" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-neutral-900">{role}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-neutral-500">{desc}</p>
                  </div>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ── Security ── */}
      <section id="security" className="bg-neutral-50 py-28">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <FadeIn className="mx-auto max-w-xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-[#1a2332] sm:text-4xl">
              Enterprise-Grade from Day One
            </h2>
            <p className="mt-4 text-base text-neutral-500">
              Security and compliance are architecture, not afterthoughts.
            </p>
          </FadeIn>

          <FadeIn delay={100} className="mt-14">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
              {SECURITY_ITEMS.map(({ Icon, label, sub }) => (
                <div
                  key={label}
                  className="flex flex-col items-center gap-2.5 rounded-2xl border border-neutral-200 bg-white px-4 py-6 text-center shadow-sm"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#1a2332]/7">
                    <Icon className="h-5 w-5 text-[#1a2332]" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-neutral-800">{label}</p>
                    <p className="mt-0.5 text-[11px] text-neutral-400">{sub}</p>
                  </div>
                </div>
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="bg-[#1a2332] py-28">
        <div className="mx-auto max-w-3xl px-6 text-center lg:px-8">
          <FadeIn>
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Ready to Transform Your Investment Operations?
            </h2>
            <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-white/55">
              Join institutional investors and fund managers who are already using SCR Platform to
              make faster, better-informed decisions.
            </p>
            <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Link
                href="/sign-in"
                className="inline-flex items-center gap-2 rounded-xl bg-white px-8 py-3.5 text-sm font-semibold text-[#1a2332] transition-all hover:bg-white/90 hover:shadow-lg"
              >
                Get Started
                <ArrowRight className="h-4 w-4" />
              </Link>
              <a
                href="mailto:contact@pampgroup.com"
                className="inline-flex items-center gap-2 rounded-xl border border-white/25 px-8 py-3.5 text-sm font-semibold text-white transition-all hover:border-white/40 hover:bg-white/5"
              >
                Book a Demo
                <ChevronRight className="h-4 w-4" />
              </a>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer id="contact" className="bg-[#0f1620] py-14">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="flex flex-col items-start justify-between gap-8 sm:flex-row sm:items-center">
            {/* Logo */}
            <div className="flex items-center gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-white/10 text-xs font-bold text-white">
                S
              </div>
              <span className="text-sm font-bold tracking-wide text-white">SCR Platform</span>
            </div>

            {/* Links */}
            <nav className="flex flex-wrap gap-6">
              {["Platform", "Features", "Security", "Legal", "Privacy Policy"].map((item) => (
                <a
                  key={item}
                  href="#"
                  className="text-xs font-medium text-white/40 transition-colors hover:text-white/70"
                >
                  {item}
                </a>
              ))}
            </nav>
          </div>

          <div className="mt-10 flex flex-col items-start justify-between gap-3 border-t border-white/8 pt-8 sm:flex-row sm:items-center">
            <p className="text-xs text-white/30">
              © 2026 SCR Platform. All rights reserved.
            </p>
            <p className="text-xs text-white/25">
              EU-hosted · GDPR-compliant · SOC 2 ready
            </p>
          </div>
        </div>
      </footer>

    </div>
  );
}
