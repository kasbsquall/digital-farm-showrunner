/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export: the app is a client-side SPA that fetches the API at the same origin
  // (NEXT_PUBLIC_API_URL=""), so it can be served as static files by the FastAPI backend
  // — one container, one URL, no CORS, no mixed-content.
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
