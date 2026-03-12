"use client";

/**
 * Admin security page — TOTP enrollment.
 *
 * Shows the current TOTP status and allows the admin to enroll or
 * verify their TOTP setup. Uses existing hooks from use-admin.ts.
 */

import { useState } from "react";
import { ShieldCheck, ShieldAlert, Loader2, KeyRound } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAdminAuthStore } from "@/lib/hooks/use-admin-auth";
import { useAdminTOTPSetup, useAdminTOTPVerify } from "@/lib/hooks/use-admin";
import { toast } from "sonner";

export default function AdminSecurityPage() {
  const admin = useAdminAuthStore((s) => s.admin);
  const totpEnabled = admin?.totp_enabled ?? false;

  const [step, setStep] = useState<"idle" | "setup" | "verify">("idle");
  const [secret, setSecret] = useState("");
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [totpCode, setTotpCode] = useState("");

  const { mutate: setupTotp, isPending: isSettingUp } = useAdminTOTPSetup();
  const { mutate: verifyTotp, isPending: isVerifying } = useAdminTOTPVerify();

  function handleStartSetup() {
    setupTotp(undefined, {
      onSuccess: (data) => {
        setSecret(data.secret);
        setQrCode(data.qr_code_base64);
        setStep("verify");
      },
      onError: (err) => {
        toast.error(
          err instanceof Error
            ? err.message
            : "No se pudo iniciar la configuracion de TOTP.",
        );
      },
    });
  }

  function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    verifyTotp(
      { totp_code: totpCode },
      {
        onSuccess: () => {
          toast.success("TOTP configurado correctamente.");
          setStep("idle");
          setTotpCode("");
          setSecret("");
          setQrCode(null);
          // Update local store
          if (admin) {
            useAdminAuthStore.getState().set_admin_auth(
              { ...admin, totp_enabled: true },
              admin.id,
            );
          }
        },
        onError: (err) => {
          toast.error(
            err instanceof Error
              ? err.message
              : "Codigo incorrecto. Intentalo de nuevo.",
          );
        },
      },
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Seguridad</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configura la autenticacion de dos factores para tu cuenta de superadmin.
        </p>
      </div>

      {/* ── TOTP Status ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <KeyRound className="h-4 w-4" />
            Autenticacion de dos factores (TOTP)
          </CardTitle>
          <CardDescription>
            Protege tu cuenta con un codigo de verificacion de 6 digitos generado
            por una app como Google Authenticator o Authy.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Status indicator */}
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-foreground">Estado:</span>
            {totpEnabled ? (
              <Badge variant="success" className="flex items-center gap-1">
                <ShieldCheck className="h-3 w-3" />
                TOTP activo
              </Badge>
            ) : (
              <Badge variant="outline" className="flex items-center gap-1">
                <ShieldAlert className="h-3 w-3" />
                No configurado
              </Badge>
            )}
          </div>

          {/* ── Idle: show setup button ── */}
          {step === "idle" && !totpEnabled && (
            <Button
              onClick={handleStartSetup}
              disabled={isSettingUp}
            >
              {isSettingUp ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generando...
                </>
              ) : (
                "Configurar TOTP"
              )}
            </Button>
          )}

          {/* ── Already enabled ── */}
          {step === "idle" && totpEnabled && (
            <p className="text-sm text-muted-foreground">
              Tu cuenta ya tiene TOTP activado. Cada vez que inicies sesion se te
              pedira un codigo de verificacion de 6 digitos.
            </p>
          )}

          {/* ── Verify step: show QR + code input ── */}
          {step === "verify" && (
            <div className="space-y-4">
              <div className="rounded-lg border border-[hsl(var(--border))] p-4 space-y-4">
                <p className="text-sm text-foreground">
                  Escanea el codigo QR con tu aplicacion de autenticacion:
                </p>

                {qrCode && (
                  <div className="flex justify-center">
                    <img
                      src={`data:image/png;base64,${qrCode}`}
                      alt="Codigo QR para TOTP"
                      className="w-48 h-48 rounded-md"
                    />
                  </div>
                )}

                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Clave secreta (manual)
                  </p>
                  <code className="block text-xs font-mono bg-muted px-3 py-2 rounded break-all select-all">
                    {secret}
                  </code>
                </div>
              </div>

              <form onSubmit={handleVerify} className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="totp-code">
                    Ingresa el codigo de 6 digitos
                  </Label>
                  <Input
                    id="totp-code"
                    value={totpCode}
                    onChange={(e) =>
                      setTotpCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                    }
                    placeholder="000000"
                    maxLength={6}
                    required
                    disabled={isVerifying}
                    className="max-w-xs font-mono text-center text-lg tracking-[0.5em]"
                    autoFocus
                  />
                </div>

                <div className="flex gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setStep("idle");
                      setTotpCode("");
                    }}
                    disabled={isVerifying}
                  >
                    Cancelar
                  </Button>
                  <Button
                    type="submit"
                    disabled={isVerifying || totpCode.length !== 6}
                  >
                    {isVerifying ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Verificando...
                      </>
                    ) : (
                      "Verificar"
                    )}
                  </Button>
                </div>
              </form>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
