import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allows testing this dev server from another device on the LAN (e.g. a
  // phone), which Next.js otherwise blocks as a cross-origin dev request.
  allowedDevOrigins: ["192.168.1.10"],
};

export default nextConfig;
