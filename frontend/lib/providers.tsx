"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { SyncProvider } from "@/lib/sync/sync-provider";

// ─── Query Client ──────────────────────────────────────────────────────────────

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // 5 minutes stale time — matches Redis TTL for most resources
        staleTime: 5 * 60 * 1000,
        // Retry up to 2 times on network errors (not 4xx/5xx)
        retry: (failureCount, error) => {
          const status = (error as { response?: { status?: number } })?.response?.status;
          // Do not retry on client errors
          if (status && status >= 400 && status < 500) return false;
          return failureCount < 2;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 4000),
        // Refetch on window focus to keep data fresh
        refetchOnWindowFocus: false,
      },
      mutations: {
        // Retry network errors (no response) up to 3 times with exponential backoff
        retry: (failureCount, error) => {
          // Only retry on network errors (no HTTP response = connection failure)
          const hasResponse = (error as { response?: unknown })?.response;
          if (hasResponse) return false;
          return failureCount < 3;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 8000),
      },
    },
  });
}

// Singleton for browser; new instance per SSR request to avoid cross-request sharing
let browserQueryClient: QueryClient | undefined;

function getQueryClient(): QueryClient {
  if (typeof window === "undefined") {
    // Server: always create a new client
    return makeQueryClient();
  }
  // Browser: reuse the existing client
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}

// ─── Theme Context ─────────────────────────────────────────────────────────────

type Theme = "light" | "dark" | "system";

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: "light" | "dark";
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "system",
  resolvedTheme: "light",
  setTheme: () => {},
});

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}

function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("system");
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");

  // Initialize from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("dentalos-theme") as Theme | null;
    if (stored && ["light", "dark", "system"].includes(stored)) {
      setThemeState(stored);
    }
  }, []);

  // Apply theme class to <html> element
  useEffect(() => {
    const root = document.documentElement;

    if (theme === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      const resolved = prefersDark ? "dark" : "light";
      setResolvedTheme(resolved);
      root.classList.toggle("dark", prefersDark);
    } else {
      setResolvedTheme(theme);
      root.classList.toggle("dark", theme === "dark");
    }
  }, [theme]);

  // Listen for system preference changes when theme is "system"
  useEffect(() => {
    if (theme !== "system") return;

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => {
      const resolved = e.matches ? "dark" : "light";
      setResolvedTheme(resolved);
      document.documentElement.classList.toggle("dark", e.matches);
    };

    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  function setTheme(newTheme: Theme) {
    setThemeState(newTheme);
    localStorage.setItem("dentalos-theme", newTheme);
  }

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

// ─── Root Providers ────────────────────────────────────────────────────────────

interface ProvidersProps {
  children: ReactNode;
}

/**
 * Root provider tree for the DentalOS frontend.
 *
 * Wraps the app with:
 * - QueryClientProvider (TanStack Query v5) — server state management
 * - ThemeProvider — light/dark mode with system preference detection
 * - Toaster — global toast notification renderer
 */
export function Providers({ children }: ProvidersProps) {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <SyncProvider>
          {children}
        </SyncProvider>
        <Toaster />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
