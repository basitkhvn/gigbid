const staticExport = process.env.STATIC_EXPORT === "1";
/** @type {import('next').NextConfig} */
export default {
  ...(staticExport ? { output: "export", trailingSlash: true } : {}),
  images: { unoptimized: true },
  reactStrictMode: true,
};
