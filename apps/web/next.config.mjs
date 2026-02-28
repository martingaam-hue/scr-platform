/** @type {import('next').NextConfig} */

const isDev = process.env.NODE_ENV === "development";

// Content-Security-Policy
// Deliberately permissive on script-src for Next.js + Clerk compatibility.
// Tighten with nonces in a future iteration if needed.
const CSP = [
  "default-src 'self'",
  // Next.js needs 'unsafe-eval' in dev (HMR); prod uses 'strict-dynamic' with nonces eventually
  `script-src 'self' 'unsafe-inline' ${isDev ? "'unsafe-eval'" : ""} https://*.clerk.accounts.dev https://clerk.shared.global https://challenges.cloudflare.com`.trim(),
  "style-src 'self' 'unsafe-inline'",
  // Clerk avatar images + our own S3 bucket
  "img-src 'self' data: blob: https://img.clerk.com https://*.amazonaws.com https://*.s3.amazonaws.com",
  "font-src 'self' data:",
  // API + Clerk auth endpoints + WebSockets
  [
    "connect-src",
    "'self'",
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    "https://*.clerk.accounts.dev",
    "https://api.clerk.com",
    "https://clerk.shared.global",
    // Clerk SSE / polling
    "wss://*.clerk.accounts.dev",
  ].join(" "),
  // Clerk OAuth popups
  "frame-src 'self' https://*.clerk.accounts.dev https://accounts.clerk.dev https://challenges.cloudflare.com",
  // Prevent embedding in iframes on other origins
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  // Block mixed-content in production
  ...(isDev ? [] : ["upgrade-insecure-requests"]),
]
  .filter(Boolean)
  .join("; ");

const securityHeaders = [
  {
    key: "X-DNS-Prefetch-Control",
    value: "on",
  },
  {
    key: "X-Frame-Options",
    value: "DENY",
  },
  {
    key: "X-Content-Type-Options",
    value: "nosniff",
  },
  {
    key: "X-XSS-Protection",
    value: "0", // Disable broken IE filter; rely on CSP
  },
  {
    key: "Referrer-Policy",
    value: "strict-origin-when-cross-origin",
  },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
  },
  {
    key: "Content-Security-Policy",
    value: CSP,
  },
  // HSTS only in production (Next.js / Vercel handles HTTPS termination)
  ...(isDev
    ? []
    : [
        {
          key: "Strict-Transport-Security",
          value: "max-age=63072000; includeSubDomains; preload",
        },
      ]),
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output bundles the minimal server for Docker production images
  output: "standalone",
  transpilePackages: ["@scr/ui", "@scr/types"],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "img.clerk.com",
      },
      {
        protocol: "https",
        hostname: "*.s3.amazonaws.com",
      },
      {
        protocol: "https",
        hostname: "*.amazonaws.com",
      },
    ],
  },
  experimental: {
    optimizePackageImports: ["lucide-react", "@scr/ui"],
  },

  async headers() {
    return [
      {
        // Apply to all routes
        source: "/(.*)",
        headers: securityHeaders,
      },
    ];
  },

  // Prevent exposing Next.js version in X-Powered-By header
  poweredByHeader: false,
};

export default nextConfig;
