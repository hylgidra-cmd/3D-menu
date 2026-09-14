import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "127.0.0.1" },
      { protocol: "http", hostname: "localhost" },
      { protocol: "http", hostname: "192.168.1.14" },
      { protocol: "http", hostname: "192.168.1.25" },
      { protocol: "https", hostname: "*.trycloudflare.com" },
    ],
  },
  // Allows testing this dev server from another device on the LAN (e.g. a
  // phone), which Next.js otherwise blocks as a cross-origin dev request.
  // The trycloudflare.com hostname changes every time the tunnel is
  // restarted, so a wildcard avoids having to edit this on every run.
  allowedDevOrigins: ["192.168.1.14", "192.168.1.20", "192.168.1.25", "*.trycloudflare.com"],
};

export default nextConfig;
