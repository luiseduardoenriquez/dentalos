"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Calendar,
  Receipt,
  BarChart3,
  Settings,
  ShieldCheck,
  Package,
  X,
  ChevronLeft,
  ChevronRight,
  Stethoscope,
  MessageSquare,
  Mail,
  Phone,
  FlaskConical,
  Video,
  Sunrise,
  CreditCard,
  ClipboardList,
  RefreshCcw,
  Star,
  Handshake,
  Wallet,
  Bot,
  Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/hooks/use-auth";

// ─── Types ────────────────────────────────────────────────────────────────────

export type UserRole =
  | "clinic_owner"
  | "doctor"
  | "assistant"
  | "receptionist"
  | "patient"
  | "superadmin";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  /** Roles that can see this item. Omit to show to all. */
  roles?: UserRole[];
  /** When true, renders as non-clickable with "(Próx.)" tooltip */
  disabled?: boolean;
  /** When true, use exact match for active state instead of startsWith */
  exact?: boolean;
  /** Feature flag key required for this item. If not enabled, shows as locked. */
  requiredFeature?: string;
  /** Label for the minimum plan (e.g. "Pro", "Clínica") — shown when locked. */
  minimumPlanLabel?: string;
}

export interface SidebarProps {
  /** Current user role for role-based nav filtering */
  role: UserRole;
  /** Controlled collapsed state */
  collapsed: boolean;
  /** Called when user clicks the collapse/expand toggle */
  onToggleCollapse: () => void;
  /** Mobile overlay: whether the sidebar is open on small screens */
  mobileOpen: boolean;
  /** Called to close mobile overlay */
  onMobileClose: () => void;
  className?: string;
}

// ─── Navigation config ────────────────────────────────────────────────────────

const NAV_ITEMS: NavItem[] = [
  {
    href: "/dashboard",
    label: "Panel",
    icon: LayoutDashboard,
    exact: true,
  },
  {
    href: "/patients",
    label: "Pacientes",
    icon: Users,
    roles: ["clinic_owner", "doctor", "assistant", "receptionist"],
  },
  {
    href: "/agenda",
    label: "Agenda",
    icon: Calendar,
    roles: ["clinic_owner", "doctor", "assistant", "receptionist"],
  },
  {
    href: "/billing",
    label: "Facturación",
    icon: Receipt,
    roles: ["clinic_owner", "receptionist"],
    requiredFeature: "billing",
    minimumPlanLabel: "Starter",
  },
  {
    href: "/compliance",
    label: "Cumplimiento",
    icon: ShieldCheck,
    roles: ["clinic_owner"],
    requiredFeature: "rips_reporting",
    minimumPlanLabel: "Pro",
  },
  {
    href: "/whatsapp",
    label: "WhatsApp",
    icon: MessageSquare,
    roles: ["clinic_owner", "doctor", "assistant", "receptionist"],
    requiredFeature: "whatsapp_notifications",
    minimumPlanLabel: "Pro",
  },
  {
    href: "/marketing",
    label: "Marketing",
    icon: Mail,
    roles: ["clinic_owner"],
    requiredFeature: "whatsapp_notifications",
    minimumPlanLabel: "Pro",
  },
  {
    href: "/analytics",
    label: "Analíticas",
    icon: BarChart3,
    roles: ["clinic_owner", "doctor"],
    requiredFeature: "analytics_basic",
    minimumPlanLabel: "Starter",
  },
  {
    href: "/calls",
    label: "Llamadas",
    icon: Phone,
    roles: ["clinic_owner", "doctor", "assistant", "receptionist"],
    requiredFeature: "billing",
    minimumPlanLabel: "Starter",
  },
  {
    href: "/lab-orders",
    label: "Laboratorio",
    icon: FlaskConical,
    roles: ["clinic_owner", "doctor", "assistant", "receptionist"],
    requiredFeature: "billing",
    minimumPlanLabel: "Starter",
  },
  {
    href: "/telemedicine",
    label: "Telemedicina",
    icon: Video,
    roles: ["clinic_owner", "doctor"],
    requiredFeature: "telehealth",
    minimumPlanLabel: "Enterprise",
  },
  {
    href: "/inventory",
    label: "Inventario",
    icon: Package,
    roles: ["clinic_owner", "assistant"],
    requiredFeature: "inventory_module",
    minimumPlanLabel: "Clínica",
  },
  {
    href: "/huddle",
    label: "Huddle",
    icon: Sunrise,
    roles: ["clinic_owner", "doctor"],
    requiredFeature: "analytics_basic",
    minimumPlanLabel: "Starter",
  },
  {
    href: "/memberships",
    label: "Membresías",
    icon: CreditCard,
    roles: ["clinic_owner"],
    requiredFeature: "billing",
    minimumPlanLabel: "Starter",
  },
  {
    href: "/intake",
    label: "Intake",
    icon: ClipboardList,
    roles: ["clinic_owner", "receptionist"],
    requiredFeature: "patient_portal",
    minimumPlanLabel: "Pro",
  },
  {
    href: "/recall",
    label: "Recall",
    icon: RefreshCcw,
    roles: ["clinic_owner"],
    requiredFeature: "patient_portal",
    minimumPlanLabel: "Pro",
  },
  {
    href: "/reputation",
    label: "Reputación",
    icon: Star,
    roles: ["clinic_owner"],
    requiredFeature: "patient_portal",
    minimumPlanLabel: "Pro",
  },
  {
    href: "/convenios",
    label: "Convenios",
    icon: Handshake,
    roles: ["clinic_owner"],
    requiredFeature: "billing",
    minimumPlanLabel: "Starter",
  },
  {
    href: "/financing",
    label: "Financiamiento",
    icon: Wallet,
    roles: ["clinic_owner"],
    requiredFeature: "billing",
    minimumPlanLabel: "Starter",
  },
  {
    href: "/chatbot",
    label: "Chatbot",
    icon: Bot,
    roles: ["clinic_owner"],
    requiredFeature: "whatsapp_notifications",
    minimumPlanLabel: "Pro",
  },
  {
    href: "/settings",
    label: "Configuración",
    icon: Settings,
    roles: ["clinic_owner", "superadmin"],
  },
];

function canSeeItem(item: NavItem, role: UserRole): boolean {
  if (!item.roles) return true;
  return item.roles.includes(role);
}

function isFeatureLocked(item: NavItem, hasFeature: (flag: string) => boolean): boolean {
  if (!item.requiredFeature) return false;
  return !hasFeature(item.requiredFeature);
}

// ─── NavLink ──────────────────────────────────────────────────────────────────

interface NavLinkProps {
  item: NavItem;
  collapsed: boolean;
  pathname: string;
  locked?: boolean;
}

function NavLink({ item, collapsed, pathname, locked = false }: NavLinkProps) {
  const isActive = item.exact
    ? pathname === item.href
    : pathname === item.href || pathname.startsWith(item.href + "/");
  const Icon = item.icon;

  const sharedClasses = cn(
    "flex items-center gap-3 rounded-md px-3 py-2.5",
    "text-sm font-medium transition-colors duration-150",
    collapsed && "justify-center px-2",
  );

  if (item.disabled) {
    return (
      <span
        className={cn(
          sharedClasses,
          "opacity-50 cursor-not-allowed select-none",
        )}
        title={collapsed ? `${item.label} (Próx.)` : "Próximamente"}
      >
        <Icon className={cn("shrink-0 opacity-70", collapsed ? "h-5 w-5" : "h-4 w-4")} />
        {!collapsed && (
          <>
            <span>{item.label}</span>
            <span className="ml-auto text-[10px] text-[hsl(var(--muted-foreground))]">(Próx.)</span>
          </>
        )}
      </span>
    );
  }

  if (locked) {
    return (
      <span
        className={cn(
          sharedClasses,
          "opacity-40 cursor-not-allowed select-none",
        )}
        title={collapsed ? `${item.label} (${item.minimumPlanLabel})` : `Requiere plan ${item.minimumPlanLabel}`}
      >
        <Icon className={cn("shrink-0 opacity-50", collapsed ? "h-5 w-5" : "h-4 w-4")} />
        {!collapsed && (
          <>
            <span>{item.label}</span>
            <span className="ml-auto flex items-center gap-1 text-[10px] text-[hsl(var(--muted-foreground))]">
              <Lock className="h-3 w-3" />
              {item.minimumPlanLabel}
            </span>
          </>
        )}
      </span>
    );
  }

  return (
    <Link
      href={item.href}
      className={cn(
        sharedClasses,
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
        isActive
          ? "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300"
          : "text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))] hover:text-foreground",
      )}
      title={collapsed ? item.label : undefined}
      aria-current={isActive ? "page" : undefined}
    >
      <Icon
        className={cn(
          "shrink-0",
          isActive ? "text-primary-600 dark:text-primary-400" : "opacity-70",
          collapsed ? "h-5 w-5" : "h-4 w-4",
        )}
      />
      {!collapsed && <span>{item.label}</span>}
    </Link>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

export function Sidebar({
  role,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onMobileClose,
  className,
}: SidebarProps) {
  const pathname = usePathname();
  const { has_feature } = useAuth();
  const visibleItems = NAV_ITEMS.filter((item) => canSeeItem(item, role));

  const sidebarContent = (
    <aside
      className={cn(
        "flex flex-col h-full border-r border-[hsl(var(--border))]",
        "bg-[hsl(var(--background))] dark:bg-[hsl(var(--card))]",
        "transition-all duration-300 ease-in-out",
        collapsed ? "w-16" : "w-64",
        className,
      )}
    >
      {/* Logo */}
      <div
        className={cn(
          "flex h-16 items-center border-b border-[hsl(var(--border))] shrink-0",
          collapsed ? "justify-center px-2" : "justify-between px-4",
        )}
      >
        {!collapsed && (
          <Link
            href="/dashboard"
            className="flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 rounded-md"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-600 shrink-0">
              <Stethoscope className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-base tracking-tight text-foreground">
              Dental<span className="text-primary-600">OS</span>
            </span>
          </Link>
        )}

        {collapsed && (
          <Link
            href="/dashboard"
            className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-600 shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600"
            title="DentalOS"
          >
            <Stethoscope className="h-4 w-4 text-white" />
          </Link>
        )}

        {/* Mobile close button */}
        <button
          type="button"
          onClick={onMobileClose}
          className="md:hidden p-1 rounded-md text-[hsl(var(--muted-foreground))] hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600"
          aria-label="Cerrar menú"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-1">
        {visibleItems.map((item) => (
          <NavLink
            key={item.href}
            item={item}
            collapsed={collapsed}
            pathname={pathname}
            locked={isFeatureLocked(item, has_feature)}
          />
        ))}
      </nav>

      {/* Collapse toggle — desktop only */}
      <div className="hidden md:flex shrink-0 border-t border-[hsl(var(--border))] p-2">
        <button
          type="button"
          onClick={onToggleCollapse}
          className={cn(
            "flex w-full items-center gap-2 rounded-md px-3 py-2",
            "text-xs text-[hsl(var(--muted-foreground))] hover:text-foreground hover:bg-[hsl(var(--muted))]",
            "transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
            collapsed && "justify-center px-2",
          )}
          aria-label={collapsed ? "Expandir menú" : "Colapsar menú"}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4 shrink-0" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4 shrink-0" />
              <span>Colapsar</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden md:flex h-full">{sidebarContent}</div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={onMobileClose}
            aria-hidden="true"
          />
          {/* Drawer */}
          <div className="relative flex h-full w-64 flex-col">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
