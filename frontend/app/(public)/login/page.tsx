"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, Loader2, Building2, CheckCircle2 } from "lucide-react";
import type { Metadata } from "next";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/lib/hooks/use-toast";
import { useLogin, useSelectTenant } from "@/lib/hooks/use-login";
import { loginSchema, type LoginFormValues } from "@/lib/validations/auth";
import type { TenantListItem } from "@/lib/hooks/use-auth";
import { cn } from "@/lib/utils";

// ─── Role Labels ──────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<string, string> = {
  clinic_owner: "Propietario",
  doctor: "Doctor",
  assistant: "Asistente",
  receptionist: "Recepcionista",
  patient: "Paciente",
  superadmin: "Superadmin",
};

function roleLabel(role: string): string {
  return ROLE_LABELS[role] ?? role;
}

// ─── Role Badge Colors ─────────────────────────────────────────────────────────

const ROLE_BADGE_COLORS: Record<string, string> = {
  clinic_owner: "bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300",
  doctor: "bg-secondary-100 text-secondary-700 dark:bg-secondary-900/40 dark:text-secondary-300",
  assistant: "bg-accent-100 text-accent-700 dark:bg-accent-900/40 dark:text-accent-300",
  receptionist: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

function roleBadgeColor(role: string): string {
  return (
    ROLE_BADGE_COLORS[role] ??
    "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
  );
}

// ─── Clinic Selector ──────────────────────────────────────────────────────────

interface ClinicSelectorProps {
  tenants: TenantListItem[];
  onSelect: (tenant_id: string) => void;
  isLoading: boolean;
}

function ClinicSelector({ tenants, onSelect, isLoading }: ClinicSelectorProps) {
  const [selected, setSelected] = useState<string>(
    tenants.find((t) => t.is_primary)?.tenant_id ?? tenants[0]?.tenant_id ?? "",
  );

  return (
    <div className="mt-6 space-y-4">
      <div>
        <p className="text-sm font-medium text-foreground mb-1">
          Selecciona la clínica
        </p>
        <p className="text-xs text-muted-foreground">
          Tu cuenta tiene acceso a múltiples clínicas.
        </p>
      </div>

      <fieldset className="space-y-2" aria-label="Selección de clínica">
        {tenants.map((tenant, idx) => (
          <label
            key={`${tenant.tenant_id}-${tenant.role ?? idx}`}
            htmlFor={`tenant-${tenant.tenant_id}`}
            className={cn(
              "flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
              selected === tenant.tenant_id
                ? "border-primary-600 bg-primary-50 dark:bg-primary-900/20"
                : "border-[hsl(var(--border))] hover:border-primary-300 hover:bg-[hsl(var(--muted))]",
            )}
          >
            <input
              id={`tenant-${tenant.tenant_id}`}
              type="radio"
              name="tenant"
              value={tenant.tenant_id}
              checked={selected === tenant.tenant_id}
              onChange={() => setSelected(tenant.tenant_id)}
              className="sr-only"
            />

            {/* Radio indicator */}
            <div
              className={cn(
                "flex-shrink-0 w-4 h-4 rounded-full border-2 transition-colors",
                selected === tenant.tenant_id
                  ? "border-primary-600 bg-primary-600"
                  : "border-slate-300 dark:border-slate-600",
              )}
              aria-hidden="true"
            >
              {selected === tenant.tenant_id && (
                <div className="w-full h-full flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-white" />
                </div>
              )}
            </div>

            <Building2
              className="h-4 w-4 text-slate-400 flex-shrink-0"
              aria-hidden="true"
            />

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {tenant.tenant_name}
              </p>
            </div>

            <span
              className={cn(
                "flex-shrink-0 text-xs font-medium px-2 py-0.5 rounded-full",
                roleBadgeColor(tenant.role),
              )}
            >
              {roleLabel(tenant.role)}
            </span>

            {tenant.is_primary && (
              <CheckCircle2
                className="h-4 w-4 text-primary-600 flex-shrink-0"
                aria-label="Clínica principal"
              />
            )}
          </label>
        ))}
      </fieldset>

      <Button
        type="button"
        className="w-full"
        disabled={!selected || isLoading}
        onClick={() => onSelect(selected)}
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Ingresando...
          </>
        ) : (
          "Continuar"
        )}
      </Button>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LoginPage() {
  const router = useRouter();
  const { error: toastError } = useToast();
  const [showPassword, setShowPassword] = useState(false);
  const [tenants, setTenants] = useState<TenantListItem[] | null>(null);
  const [preAuthToken, setPreAuthToken] = useState<string>("");

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const { mutate: login, isPending: isLoginPending } = useLogin();
  const { mutate: selectTenant, isPending: isSelectPending } = useSelectTenant();

  function onSubmit(values: LoginFormValues) {
    login(values, {
      onSuccess: (data) => {
        if (data.requires_tenant_selection && data.tenants) {
          // Show clinic selector
          setTenants(data.tenants);
          setPreAuthToken(data.pre_auth_token ?? "");
        } else {
          // Direct redirect to dashboard
          router.replace("/dashboard");
        }
      },
      onError: (err) => {
        const apiErr = err as { response?: { data?: { message?: string } } };
        toastError(
          "Error al iniciar sesión",
          apiErr.response?.data?.message ??
            "Verifica tu correo y contraseña e inténtalo de nuevo.",
        );
      },
    });
  }

  function handleSelectTenant(tenant_id: string) {
    selectTenant(
      { pre_auth_token: preAuthToken, tenant_id },
      {
        onSuccess: () => {
          router.replace("/dashboard");
        },
        onError: (err) => {
          const apiErr = err as { response?: { data?: { message?: string } } };
          toastError(
            "Error al seleccionar clínica",
            apiErr.response?.data?.message ?? "Inténtalo de nuevo.",
          );
        },
      },
    );
  }

  const isPending = isLoginPending || isSelectPending;

  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-foreground">Iniciar sesión</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Bienvenido de vuelta a DentalOS.
        </p>
      </div>

      {/* Login form — hidden when clinic selector is shown */}
      {!tenants && (
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
          {/* Email */}
          <div className="space-y-1.5">
            <Label htmlFor="email" required>
              Correo electrónico
            </Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="doctor@miclínica.com"
              aria-invalid={!!errors.email}
              aria-describedby={errors.email ? "email-error" : undefined}
              {...register("email")}
            />
            {errors.email && (
              <p id="email-error" className="text-xs text-destructive-600 dark:text-destructive-400">
                {errors.email.message}
              </p>
            )}
          </div>

          {/* Password */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="password" required>
                Contraseña
              </Label>
              <Link
                href="/forgot-password"
                className="text-xs text-primary-600 hover:underline dark:text-primary-400"
              >
                ¿Olvidaste tu contraseña?
              </Link>
            </div>
            <Input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              placeholder="••••••••"
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? "password-error" : undefined}
              endAdornment={
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                  className="pointer-events-auto text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <Eye className="h-4 w-4" aria-hidden="true" />
                  )}
                </button>
              }
              {...register("password")}
            />
            {errors.password && (
              <p id="password-error" className="text-xs text-destructive-600 dark:text-destructive-400">
                {errors.password.message}
              </p>
            )}
          </div>

          {/* Submit */}
          <Button type="submit" className="w-full" disabled={isPending}>
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Iniciando sesión...
              </>
            ) : (
              "Iniciar sesión"
            )}
          </Button>
        </form>
      )}

      {/* Clinic selector — shown after multi-tenant login */}
      {tenants && (
        <ClinicSelector
          tenants={tenants}
          onSelect={handleSelectTenant}
          isLoading={isSelectPending}
        />
      )}

      {/* Footer links */}
      {!tenants && (
        <div className="mt-6 space-y-2 text-center text-sm text-muted-foreground">
          <p>
            ¿No tienes cuenta?{" "}
            <Link
              href="/register"
              className="font-medium text-primary-600 hover:underline dark:text-primary-400"
            >
              Registrar clínica
            </Link>
          </p>
          <p>
            ¿Eres paciente?{" "}
            <Link
              href="/portal/login"
              className="font-medium text-primary-600 hover:underline dark:text-primary-400"
            >
              Ingresa a tu portal &rarr;
            </Link>
          </p>
        </div>
      )}
    </div>
  );
}
