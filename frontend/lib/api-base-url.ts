const RAW_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export function getApiBaseUrl(): string {
  // In development we always use relative URLs so that
  // Next.js rewrites/proxy decide where the backend lives (localhost, ngrok, etc.).
  if (process.env.NODE_ENV === "development") {
    return "";
  }

  return RAW_API_BASE_URL;
}

