/** @type {import('next').NextConfig} */
const nextConfig = {
  // Standalone output keeps the Docker image small and self-contained
  // (bundles only the traced dependencies + a minimal server) — see
  // frontend/Dockerfile.
  output: "standalone",
};

module.exports = nextConfig;
