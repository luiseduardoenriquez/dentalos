import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN || "",
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "development",
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0.1,

  // Strip PHI from breadcrumbs
  beforeBreadcrumb(breadcrumb) {
    if (breadcrumb.category === "xhr" || breadcrumb.category === "fetch") {
      // Strip request/response data that may contain PHI
      if (breadcrumb.data) {
        delete breadcrumb.data.request_body;
        delete breadcrumb.data.response_body;
      }
    }
    return breadcrumb;
  },

  // Strip PHI from events
  beforeSend(event) {
    // Remove request body data (may contain PHI)
    if (event.request) {
      delete event.request.data;
      // Scrub query strings for tenant schemas
      if (typeof event.request.query_string === "string") {
        event.request.query_string = event.request.query_string.replace(
          /tn_[a-z0-9_]+/g,
          "[TENANT]",
        );
      }
    }

    // Scrub user context (keep id only)
    if (event.user) {
      event.user = { id: event.user.id };
    }

    return event;
  },
});
