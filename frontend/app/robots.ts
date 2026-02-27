import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/pricing", "/blog"],
        disallow: [
          "/dashboard",
          "/patients",
          "/agenda",
          "/odontogram",
          "/billing",
          "/settings",
          "/team",
          "/reports",
          "/admin",
          "/portal",
          "/login",
          "/register",
          "/forgot-password",
          "/reset-password",
        ],
      },
    ],
    sitemap: "https://dentalos.co/sitemap.xml",
  };
}
