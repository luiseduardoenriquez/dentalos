import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";
import withBundleAnalyzer from "@next/bundle-analyzer";
import { withSerwist } from "@serwist/turbopack";

const analyzer = withBundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

const isDev = process.env.NODE_ENV === "development";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  typescript: {
    // TODO: Fix pre-existing TS2339 errors across 276 locations (unrelated to PWA)
    ignoreBuildErrors: true,
  },
  // env: {
  //   // When empty string, api-client uses relative URLs → requests go through Next.js rewrites proxy
  //   // This enables external access (ngrok) without CORS issues
  //   NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "",
  // },
  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 3600,
    remotePatterns: [
      {
        protocol: "https",
        hostname: "*.hetzner.com",
      },
      {
        protocol: "http",
        hostname: "localhost",
        port: "9000",
      },
    ],
  },
  async rewrites() {
    // Proxy API calls through Next.js so external devices (ngrok) can reach the backend
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(self), geolocation=()",
          },
          ...(isDev ? [] : [{
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains; preload",
          }]),
          {
            key: "Content-Security-Policy",
            // unsafe-eval and unsafe-inline are required for Next.js runtime
            value:
              "default-src 'self'; " +
              "script-src 'self' 'unsafe-eval' 'unsafe-inline'; " +
              "style-src 'self' 'unsafe-inline'; " +
              "img-src 'self' data: blob: https:; " +
              "font-src 'self' data:; " +
              `media-src 'self' blob:${isDev ? " http://localhost:* http://127.0.0.1:*" : ""} https:; ` +
              `connect-src 'self' https:${isDev ? " http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:* wss://localhost:*" : ""}; ` +
              "frame-ancestors 'none';",
          },
        ],
      },
    ];
  },
};

export default withSerwist(analyzer(withSentryConfig(nextConfig, {
  // Suppresses source map uploading logs during build
  silent: true,
})) as NextConfig);
