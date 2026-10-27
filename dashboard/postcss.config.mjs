/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    // Tailwind v4 moved the PostCSS plugin into its own package, and bundles
    // the vendor prefixing autoprefixer was here for.
    "@tailwindcss/postcss": {},
  },
};

export default config;
