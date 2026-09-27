import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // When proxied behind rajeevg.com/solutions/ai-discovery, BASE_PATH is set at
  // build time so every internal link and asset is prefixed correctly. Empty in
  // local dev, tests and CI.
  basePath: process.env.BASE_PATH || undefined,
  reactStrictMode: true,
  poweredByHeader: false,
  devIndicators: false,
  agentRules: false,
};

export default nextConfig;
