/**
 * Next.js 16 Middleware for route protection.
 *
 * Strategy: Use the presence of the `dentalos_refresh` HttpOnly cookie as a
 * proxy for authentication state. The actual JWT validation happens server-side
 * in FastAPI — this middleware only handles redirects based on whether the user
 * appears to be logged in or not.
 *
 * Note: In Next.js 16, this file is `middleware.ts` at the project root.
 * The App Router uses `proxy.ts` for some advanced cases, but standard
 * middleware for auth gating lives here.
 *
 * Cookie name must match what the backend sets in POST /auth/login and
 * POST /auth/refresh (see backend/app/api/v1/auth/router.py).
 */

import { type NextRequest, NextResponse } from "next/server";

// ─── Route Classification ─────────────────────────────────────────────────────

/**
 * Routes that do NOT require authentication.
 * Authenticated users visiting these are redirected to /dashboard.
 */
const PUBLIC_ROUTES = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/accept-invite",
  "/onboarding",
];

/**
 * Routes that are always accessible regardless of auth state.
 * Includes Next.js internals and public-facing portal/marketing pages.
 */
const ALWAYS_ACCESSIBLE_PREFIXES = [
  "/_next",
  "/favicon.ico",
  "/robots.txt",
  "/sitemap.xml",
  "/api/v1/public", // Backend public API (served by FastAPI, not Next)
];

// ─── Cookie Name ──────────────────────────────────────────────────────────────

/**
 * The refresh token cookie name set by the backend.
 * Must match `REFRESH_TOKEN_COOKIE_NAME` in backend config.
 */
const REFRESH_TOKEN_COOKIE = "dentalos_refresh";

// ─── Middleware ───────────────────────────────────────────────────────────────

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  // Allow Next.js internals and static files to pass through immediately
  for (const prefix of ALWAYS_ACCESSIBLE_PREFIXES) {
    if (pathname.startsWith(prefix)) {
      return NextResponse.next();
    }
  }

  // Check if the user appears authenticated by refresh cookie presence
  const hasRefreshCookie = request.cookies.has(REFRESH_TOKEN_COOKIE);

  const isPublicRoute = PUBLIC_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );

  const isDashboardRoute =
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/patients") ||
    pathname.startsWith("/agenda") ||
    pathname.startsWith("/odontogram") ||
    pathname.startsWith("/billing") ||
    pathname.startsWith("/settings") ||
    pathname.startsWith("/team") ||
    pathname.startsWith("/reports") ||
    pathname.startsWith("/admin");

  const isPortalRoute = pathname.startsWith("/portal");

  // Case 1: Unauthenticated user trying to access protected dashboard routes
  if (!hasRefreshCookie && isDashboardRoute) {
    const loginUrl = new URL("/login", request.url);
    // Preserve the intended destination for post-login redirect
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Case 2: Unauthenticated user trying to access portal routes
  if (!hasRefreshCookie && isPortalRoute) {
    const portalLoginUrl = new URL("/portal/login", request.url);
    portalLoginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(portalLoginUrl);
  }

  // Case 3: Authenticated user visiting a public auth route (login, register, etc.)
  if (hasRefreshCookie && isPublicRoute) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // Case 4: Root redirect — "/" goes to dashboard if logged in, login if not
  if (pathname === "/") {
    if (hasRefreshCookie) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    } else {
      return NextResponse.redirect(new URL("/login", request.url));
    }
  }

  return NextResponse.next();
}

// ─── Matcher ──────────────────────────────────────────────────────────────────

/**
 * Matcher excludes Next.js static assets and image optimization routes
 * to avoid unnecessary middleware invocations.
 */
export const config = {
  matcher: [
    /*
     * Match all request paths EXCEPT:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico, sitemap.xml, robots.txt
     */
    "/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};
