/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@scr/ui", "@scr/types"],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "img.clerk.com",
      },
    ],
  },
  experimental: {
    optimizePackageImports: ["lucide-react", "@scr/ui"],
  },
};

export default nextConfig;
