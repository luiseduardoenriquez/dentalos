import { createSerwistRoute } from "@serwist/turbopack";

export const { dynamic, dynamicParams, revalidate, generateStaticParams, GET } =
  createSerwistRoute({
    // offline.html is auto-precached from public/ — do NOT add it here to avoid
    // "add-to-cache-list-conflicting-entries" which kills SW registration.
    swSrc: "app/sw.ts",
    useNativeEsbuild: true,
  });
