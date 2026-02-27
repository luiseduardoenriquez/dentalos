import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN || "",
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "development",
  tracesSampleRate: 0.1,

  beforeSend(event) {
    // Remove request body data (may contain PHI)
    if (event.request) {
      delete event.request.data;
    }
    // Scrub user context
    if (event.user) {
      event.user = { id: event.user.id };
    }
    return event;
  },
});
