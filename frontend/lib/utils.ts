import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merges Tailwind CSS classes without conflicts.
 * Combines clsx (conditional classes) with tailwind-merge (conflict resolution).
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Formats an integer (cents) as a localized currency string.
 * Backend always sends money as integer cents — never floats.
 *
 * @param cents - Amount in cents (e.g. 150000 = COP 1.500)
 * @param currency - ISO 4217 currency code, defaults to COP
 */
export function formatCurrency(cents: number, currency = "COP"): string {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

/**
 * Formats a date string or Date object using Colombian locale.
 *
 * @param date - ISO date string or Date object
 * @param options - Optional Intl.DateTimeFormatOptions overrides
 */
export function formatDate(date: string | Date, options?: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    ...options,
  }).format(new Date(date));
}

/**
 * Formats a date+time string using Colombian locale (date + short time).
 *
 * @param date - ISO datetime string or Date object
 */
export function formatDateTime(date: string | Date): string {
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(date));
}

/**
 * Formats a time-only string using Colombian locale.
 *
 * @param date - ISO datetime string or Date object
 */
export function formatTime(date: string | Date): string {
  return new Intl.DateTimeFormat("es-CO", {
    timeStyle: "short",
  }).format(new Date(date));
}

/**
 * Returns the initials from a full name (up to 2 characters).
 * Used for avatar fallbacks.
 *
 * @param name - Full name string
 */
export function getInitials(name: string | undefined | null): string {
  if (!name) return "";
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
}

/**
 * Truncates a string to a maximum length, appending "..." if truncated.
 *
 * @param str - Input string
 * @param maxLength - Maximum character length before truncation
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return `${str.slice(0, maxLength - 3)}...`;
}

/**
 * Converts a snake_case string to a readable title.
 * e.g. "clinic_owner" → "Clinic owner"
 *
 * @param str - snake_case string
 */
export function snakeToTitle(str: string): string {
  return str.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

/**
 * Checks if a value is a non-empty string.
 */
export function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

/**
 * Builds query string from an object, omitting null/undefined/empty values.
 *
 * @param params - Record of query parameters
 */
export function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      searchParams.set(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

/**
 * Pauses execution for a given number of milliseconds.
 * Useful for minimum loading state duration in tests / animations.
 *
 * @param ms - Milliseconds to sleep
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
