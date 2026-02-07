import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/compliance',
        destination: '/?module=compliance',
      },
      {
        source: '/monitoring',
        destination: '/?module=monitoring',
      },
      {
        source: '/partners',
        destination: '/?module=partners',
      },
      {
        source: '/approvals',
        destination: '/?module=approvals',
      },
      {
        source: '/reconciliation',
        destination: '/?module=reconciliation',
      },
    ];
  },
};

export default nextConfig;
