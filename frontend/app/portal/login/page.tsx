"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setPortalAccessToken, portalApiPost } from "@/lib/portal-api-client";
import { usePortalAuthStore } from "@/lib/stores/portal-auth-store";

// ─── Types ────────────────────────────────────────────────────────────────────

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  must_change_password?: boolean;
  patient: {
    id: string;
    first_name: string;
    last_name: string;
    email: string | null;
    phone: string | null;
  };
}

interface MagicLinkResponse {
  status: string;
  message: string;
  expires_in_minutes: number;
  channel: string;
}

// ─── Login Page ─────────────────────────────────────────────────────────────

export default function PortalLoginPage() {
  return (
    <Suspense>
      <PortalLoginContent />
    </Suspense>
  );
}

function PortalLoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") || "/portal/dashboard";
  const { set_portal_auth } = usePortalAuthStore();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [tenantId, setTenantId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showMagicLink, setShowMagicLink] = useState(false);
  const [magicLinkSent, setMagicLinkSent] = useState(false);
  const [magicLinkChannel, setMagicLinkChannel] = useState<"email" | "whatsapp">("email");

  // Password change state (shown after login when must_change_password is true)
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pendingLoginData, setPendingLoginData] = useState<LoginResponse | null>(null);

  function completeLogin(data: LoginResponse) {
    setPortalAccessToken(data.access_token);
    set_portal_auth({
      id: data.patient.id,
      first_name: data.patient.first_name,
      last_name: data.patient.last_name,
      email: data.patient.email,
      phone: data.patient.phone,
    });
    router.replace(redirect);
  }

  async function handlePasswordLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const data = await portalApiPost<LoginResponse>("/portal/auth/login", {
        login_method: "password",
        identifier,
        password,
        tenant_id: tenantId,
      });

      if (data.must_change_password) {
        // Store token so we can call change-password, but show the change form
        setPortalAccessToken(data.access_token);
        setPendingLoginData(data);
        setShowPasswordChange(true);
      } else {
        completeLogin(data);
      }
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string }; status?: number } };
      if (axiosErr.response?.status === 429) {
        setError("Demasiados intentos. Intenta de nuevo más tarde.");
      } else {
        setError(axiosErr.response?.data?.message || "Credenciales inválidas.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    if (newPassword.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }

    setLoading(true);
    try {
      await portalApiPost("/portal/auth/change-password", {
        new_password: newPassword,
      });
      if (pendingLoginData) {
        completeLogin(pendingLoginData);
      }
    } catch {
      setError("Error al cambiar la contraseña. Inténtalo de nuevo.");
    } finally {
      setLoading(false);
    }
  }

  async function handleKeepCurrentPassword() {
    setError(null);
    setLoading(true);
    try {
      // "Keep current" sends the password they just typed to clear the flag
      await portalApiPost("/portal/auth/change-password", {
        new_password: password,
      });
      if (pendingLoginData) {
        completeLogin(pendingLoginData);
      }
    } catch {
      setError("Error al confirmar la contraseña. Inténtalo de nuevo.");
    } finally {
      setLoading(false);
    }
  }

  async function handleMagicLink() {
    setError(null);
    setLoading(true);

    try {
      await portalApiPost<MagicLinkResponse>("/portal/auth/login", {
        login_method: "magic_link",
        identifier,
        magic_link_channel: magicLinkChannel,
        tenant_id: tenantId,
      });
      setMagicLinkSent(true);
    } catch {
      setError("Error al enviar el enlace. Inténtalo de nuevo.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-zinc-950 p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="mx-auto w-12 h-12 rounded-xl bg-primary-600 flex items-center justify-center text-white text-xl font-bold">
            D
          </div>
          <h1 className="text-2xl font-bold text-[hsl(var(--foreground))]">
            Portal del Paciente
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Ingresa a tu cuenta para ver tus citas, tratamientos y documentos
          </p>
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] shadow-sm p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 text-sm text-red-700 dark:text-red-400">
              {error}
            </div>
          )}

          {showPasswordChange ? (
            <form onSubmit={handleChangePassword} className="space-y-4">
              <div className="text-center space-y-1 pb-2">
                <h2 className="text-lg font-semibold text-[hsl(var(--foreground))]">Cambiar contraseña</h2>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  Tu contraseña es temporal. Por favor elige una nueva contraseña o confirma la actual.
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5">
                  Nueva contraseña
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Mínimo 8 caracteres"
                  required
                  minLength={8}
                  className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5">
                  Confirmar contraseña
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repite la contraseña"
                  required
                  minLength={8}
                  className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Guardando..." : "Cambiar contraseña"}
              </button>
              <div className="text-center">
                <button
                  type="button"
                  onClick={handleKeepCurrentPassword}
                  disabled={loading}
                  className="text-sm text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                >
                  Continuar con la contraseña actual
                </button>
              </div>
            </form>
          ) : magicLinkSent ? (
            <div className="text-center space-y-3 py-4">
              <div className="mx-auto w-16 h-16 rounded-full bg-green-100 dark:bg-green-950/30 flex items-center justify-center">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold">Enlace enviado</h2>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Revisa tu {magicLinkChannel === "email" ? "correo" : "WhatsApp"} para acceder a tu cuenta.
                El enlace expira en 15 minutos.
              </p>
              <button
                onClick={() => { setMagicLinkSent(false); setShowMagicLink(false); }}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                Volver al inicio de sesión
              </button>
            </div>
          ) : showMagicLink ? (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">Recibir enlace de acceso</h2>
              <div>
                <label className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5">
                  Email o teléfono
                </label>
                <input
                  type="text"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="tu@email.com o +57..."
                  className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5">
                  Enviar por
                </label>
                <div className="flex gap-3">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      checked={magicLinkChannel === "email"}
                      onChange={() => setMagicLinkChannel("email")}
                      className="text-primary-600"
                    />
                    Email
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      checked={magicLinkChannel === "whatsapp"}
                      onChange={() => setMagicLinkChannel("whatsapp")}
                      className="text-primary-600"
                    />
                    WhatsApp
                  </label>
                </div>
              </div>
              <button
                onClick={handleMagicLink}
                disabled={loading || !identifier}
                className="w-full py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Enviando..." : "Enviar enlace"}
              </button>
              <button
                onClick={() => setShowMagicLink(false)}
                className="w-full text-sm text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
              >
                Volver a inicio de sesión con contraseña
              </button>
            </div>
          ) : (
            <form onSubmit={handlePasswordLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5">
                  Clínica
                </label>
                <input
                  type="text"
                  value={tenantId}
                  onChange={(e) => setTenantId(e.target.value)}
                  placeholder="ID de la clínica"
                  required
                  className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5">
                  Email o teléfono
                </label>
                <input
                  type="text"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="tu@email.com o +57..."
                  required
                  className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5">
                  Contraseña
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Tu contraseña"
                  required
                  className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Ingresando..." : "Ingresar"}
              </button>
              <div className="text-center">
                <button
                  type="button"
                  onClick={() => setShowMagicLink(true)}
                  className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                >
                  Recibir enlace de acceso
                </button>
              </div>
            </form>
          )}
        </div>

        <p className="text-center text-xs text-[hsl(var(--muted-foreground))]">
          Portal del paciente de DentalOS
        </p>
      </div>
    </div>
  );
}
