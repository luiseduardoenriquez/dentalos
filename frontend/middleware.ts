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
  "/serwist/",      // Service worker route handler
  "/offline.html",  // Offline fallback page
  "/icons/",        // PWA icons
];

// ─── Cookie Name ──────────────────────────────────────────────────────────────

/**
 * Session indicator cookie set by the frontend after a successful login.
 * This is NOT a security token — it's a lightweight flag so the middleware
 * can gate routes without needing the HttpOnly refresh cookie (which is
 * scoped to the backend origin/path and invisible here).
 */
const SESSION_COOKIE = "dentalos_session";

/**
 * Session indicator cookie set by the admin auth store after a successful
 * admin login. Separate from the clinic session cookie.
 */
const ADMIN_SESSION_COOKIE = "dentalos_admin_session";

// ─── Middleware ───────────────────────────────────────────────────────────────

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  // Allow Next.js internals and static files to pass through immediately
  for (const prefix of ALWAYS_ACCESSIBLE_PREFIXES) {
    if (pathname.startsWith(prefix)) {
      return NextResponse.next();
    }
  }

  // ── Admin routes: separate auth flow ─────────────────────────────────────
  // /admin/login is always accessible (it IS the admin login page).
  // Other /admin/* routes require the admin session cookie.
  if (pathname.startsWith("/admin")) {
    const isAdminLogin =
      pathname === "/admin/login" || pathname.startsWith("/admin/login/");

    if (isAdminLogin) {
      // Already logged-in admin visiting login → send to admin dashboard
      if (request.cookies.has(ADMIN_SESSION_COOKIE)) {
        return NextResponse.redirect(new URL("/admin/dashboard", request.url));
      }
      return NextResponse.next();
    }

    // Protected admin route — require admin session cookie
    if (!request.cookies.has(ADMIN_SESSION_COOKIE)) {
      return NextResponse.redirect(new URL("/admin/login", request.url));
    }

    return NextResponse.next();
  }

  // ── Clinic routes ────────────────────────────────────────────────────────

  // Check if the user appears authenticated by session cookie presence
  const hasSessionCookie = request.cookies.has(SESSION_COOKIE);

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
    pathname.startsWith("/analytics") ||
    pathname.startsWith("/compliance") ||
    pathname.startsWith("/inventory") ||
    pathname.startsWith("/whatsapp") ||
    pathname.startsWith("/marketing") ||
    pathname.startsWith("/chatbot") ||
    pathname.startsWith("/calls") ||
    pathname.startsWith("/lab-orders") ||
    pathname.startsWith("/telemedicine") ||
    pathname.startsWith("/recall") ||
    pathname.startsWith("/intake") ||
    pathname.startsWith("/reputation") ||
    pathname.startsWith("/memberships") ||
    pathname.startsWith("/convenios") ||
    pathname.startsWith("/financing") ||
    pathname.startsWith("/referral-program") ||
    pathname.startsWith("/huddle");

  const isPortalRoute = pathname.startsWith("/portal");

  // Case 1: Unauthenticated user trying to access protected dashboard routes
  if (!hasSessionCookie && isDashboardRoute) {
    const loginUrl = new URL("/login", request.url);
    // Preserve the intended destination for post-login redirect
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Case 2: Unauthenticated user trying to access portal routes
  // Portal login and registration pages are always accessible
  const isPortalPublicRoute =
    pathname === "/portal/login" ||
    pathname.startsWith("/portal/login/") ||
    pathname === "/portal/register" ||
    pathname.startsWith("/portal/register/");

  if (!hasSessionCookie && isPortalRoute && !isPortalPublicRoute) {
    const portalLoginUrl = new URL("/portal/login", request.url);
    portalLoginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(portalLoginUrl);
  }

  // Case 3: Marketing routes — always accessible, no redirects
  const MARKETING_ROUTES = ["/", "/pricing", "/blog"];
  const isMarketingRoute = MARKETING_ROUTES.some(
    (r) => pathname === r || pathname.startsWith(`${r}/`),
  );
  if (isMarketingRoute) return NextResponse.next();

  // Case 4: Authenticated user visiting a public auth route (login, register, etc.)
  if (hasSessionCookie && isPublicRoute) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
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
    "/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt|serwist/.*|offline\\.html).*)",
  ],
};
