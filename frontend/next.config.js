/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow TMDB images and Google avatar images
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "image.tmdb.org",
        pathname: "/t/p/**",
      },
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
      },
    ],
  },

  // Strict mode for better dev experience
  reactStrictMode: true,
};

module.exports = nextConfig;
