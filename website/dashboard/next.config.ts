import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  async rewrites() {
    const apiUrl = process.env.BACKEND_URL ?? "http://45.77.233.102:8003";
    return [
      {
        source: "/backend/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
