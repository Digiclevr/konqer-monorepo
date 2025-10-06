/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',  // Static export pour Kinsta
  images: {
    unoptimized: true
  },
  trailingSlash: true,
  distDir: 'out',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://api.konqer.app',
  }
};

export default nextConfig;
