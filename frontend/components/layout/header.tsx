"use client";

import * as React from "react";
import { Menu, Search, Bell, LogOut, User, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getInitials } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<string, string> = {
  clinic_owner: "Propietario",
  doctor: "Doctor",
  assistant: "Asistente",
  receptionist: "Recepcionista",
  patient: "Paciente",
  superadmin: "Superadmin",
};

export interface HeaderProps {
  /** Clinic display name shown on the left */
  clinicName: string;
  /** Full name of the logged-in user */
  userName: string;
  /** User role code */
  userRole: string;
  /** Optional avatar image URL */
  userAvatarUrl?: string;
  /** Number of unread notifications */
  notificationCount?: number;
  /** Called when mobile hamburger menu is pressed */
  onMenuToggle: () => void;
  /** Called when user clicks "Cerrar sesión" */
  onSignOut: () => void;
  /** Called when search trigger is clicked */
  onSearchClick?: () => void;
  /** Called when notification bell is clicked */
  onNotificationClick?: () => void;
  /** Optional sync status indicator rendered in the header */
  syncIndicator?: React.ReactNode;
  className?: string;
}

// ─── Notification Bell ────────────────────────────────────────────────────────

interface NotificationBellProps {
  count?: number;
  onClick?: () => void;
}

function NotificationBell({ count = 0, onClick }: NotificationBellProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "relative flex h-9 w-9 items-center justify-center rounded-md",
        "text-[hsl(var(--muted-foreground))] hover:text-foreground hover:bg-[hsl(var(--muted))]",
        "transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
      )}
      aria-label={
        count > 0 ? `${count} notificaciones sin leer` : "Notificaciones"
      }
    >
      <Bell className="h-5 w-5" />
      {count > 0 && (
        <span
          className={cn(
            "absolute right-1 top-1 flex h-4 w-4 items-center justify-center",
            "rounded-full bg-destructive-600 text-white text-[10px] font-bold",
          )}
          aria-hidden="true"
        >
          {count > 9 ? "9+" : count}
        </span>
      )}
    </button>
  );
}

// ─── Search Trigger ───────────────────────────────────────────────────────────

interface SearchTriggerProps {
  onClick?: () => void;
}

function SearchTrigger({ onClick }: SearchTriggerProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "hidden sm:flex items-center gap-2 h-9 rounded-md border border-[hsl(var(--border))]",
        "bg-[hsl(var(--muted))] px-3 text-sm text-[hsl(var(--muted-foreground))]",
        "hover:bg-[hsl(var(--background))] hover:text-foreground transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
        "min-w-[200px] lg:min-w-[280px]",
      )}
      aria-label="Buscar pacientes"
    >
      <Search className="h-4 w-4 shrink-0" />
      <span>Buscar pacientes...</span>
      <kbd className="ml-auto hidden lg:inline-flex h-5 items-center gap-1 rounded border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-1.5 font-mono text-[10px] text-[hsl(var(--muted-foreground))]">
        ⌘K
      </kbd>
    </button>
  );
}

// ─── Header ───────────────────────────────────────────────────────────────────

export function Header({
  clinicName,
  userName,
  userRole,
  userAvatarUrl,
  notificationCount = 0,
  onMenuToggle,
  onSignOut,
  onSearchClick,
  onNotificationClick,
  syncIndicator,
  className,
}: HeaderProps) {
  const roleLabel = ROLE_LABELS[userRole] ?? userRole;
  const initials = getInitials(userName);

  return (
    <header
      className={cn(
        "sticky top-0 z-40 flex h-16 items-center gap-3 border-b border-[hsl(var(--border))]",
        "bg-[hsl(var(--background))]/95 backdrop-blur-sm px-4",
        className,
      )}
    >
      {/* Hamburger — mobile only */}
      <button
        type="button"
        onClick={onMenuToggle}
        className={cn(
          "flex md:hidden h-9 w-9 items-center justify-center rounded-md",
          "text-[hsl(var(--muted-foreground))] hover:text-foreground hover:bg-[hsl(var(--muted))]",
          "transition-colors duration-150 shrink-0",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
        )}
        aria-label="Abrir menú"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Clinic name */}
      <div className="flex-1 min-w-0">
        <h1 className="text-sm font-semibold text-foreground truncate md:text-base">
          {clinicName}
        </h1>
      </div>

      {/* Search trigger */}
      <SearchTrigger onClick={onSearchClick} />

      {/* Right actions */}
      <div className="flex items-center gap-1 shrink-0">
        {/* Mobile search icon */}
        <button
          type="button"
          onClick={onSearchClick}
          className={cn(
            "flex sm:hidden h-9 w-9 items-center justify-center rounded-md",
            "text-[hsl(var(--muted-foreground))] hover:text-foreground hover:bg-[hsl(var(--muted))]",
            "transition-colors duration-150",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
          )}
          aria-label="Buscar"
        >
          <Search className="h-5 w-5" />
        </button>

        {/* Sync status */}
        {syncIndicator}

        {/* Notifications */}
        <NotificationBell count={notificationCount} onClick={onNotificationClick} />

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className={cn(
                "flex items-center gap-2 rounded-md px-2 py-1.5",
                "hover:bg-[hsl(var(--muted))] transition-colors duration-150",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
              )}
              aria-label="Menú de usuario"
            >
              <Avatar size="sm">
                {userAvatarUrl && (
                  <AvatarImage src={userAvatarUrl} alt={userName} />
                )}
                <AvatarFallback>{initials}</AvatarFallback>
              </Avatar>
              <div className="hidden md:flex flex-col items-start leading-none">
                <span className="text-sm font-medium text-foreground max-w-[120px] truncate">
                  {userName}
                </span>
                <span className="text-xs text-[hsl(var(--muted-foreground))]">
                  {roleLabel}
                </span>
              </div>
              <ChevronDown className="hidden md:block h-3.5 w-3.5 text-[hsl(var(--muted-foreground))]" />
            </button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-0.5">
                <span className="text-sm font-semibold text-foreground truncate">
                  {userName}
                </span>
                <span className="text-xs text-[hsl(var(--muted-foreground))]">
                  {roleLabel}
                </span>
              </div>
            </DropdownMenuLabel>

            <DropdownMenuSeparator />

            <DropdownMenuItem>
              <User className="h-4 w-4" />
              Mi perfil
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              destructive
              onClick={onSignOut}
            >
              <LogOut className="h-4 w-4" />
              Cerrar sesión
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
