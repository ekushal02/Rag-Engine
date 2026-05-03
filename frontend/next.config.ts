// frontend/next.config.ts
import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  output: "standalone",   // required for the Docker multi-stage build
}

export default nextConfig