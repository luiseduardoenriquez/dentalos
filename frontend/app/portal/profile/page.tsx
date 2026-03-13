"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { usePortalMe, usePortalUpdateProfile } from "@/lib/hooks/use-portal";

export default function ProfilePage() {
  const { data: profile, isLoading, isError } = usePortalMe();
  const { mutate: updateProfile, isPending } = usePortalUpdateProfile();

  const [form, setForm] = useState({
    phone: "",
    email: "",
    address: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
  });

  useEffect(() => {
    if (profile) {
      setForm({
        phone: profile.phone ?? "",
        email: profile.email ?? "",
        address: profile.address ?? "",
        emergency_contact_name: profile.emergency_contact_name ?? "",
        emergency_contact_phone: profile.emergency_contact_phone ?? "",
      });
    }
  }, [profile]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    updateProfile(form, {
      onSuccess: () => {
        toast.success("Perfil actualizado correctamente.");
      },
      onError: () => {
        toast.error("No se pudo actualizar el perfil. Inténtalo de nuevo.");
      },
    });
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-sm text-muted-foreground">Cargando perfil...</p>
      </div>
    );
  }

  if (isError || !profile) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-sm text-destructive">
          No se pudo cargar tu perfil. Recarga la página.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 md:px-6">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight" style={{ color: "hsl(var(--foreground))" }}>
        Mi perfil
      </h1>

      {/* Read-only identity card */}
      <div className="mb-6 rounded-xl border bg-white p-6 shadow-sm dark:bg-gray-900 dark:border-gray-700">
        <h2 className="mb-4 text-base font-medium" style={{ color: "hsl(var(--foreground))" }}>
          Datos de identidad
        </h2>
        <p className="mb-4 text-xs text-muted-foreground">
          Por razones de seguridad y normativa, estos datos no pueden modificarse desde el portal. Si necesitas corregirlos, comunícate con la clínica.
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Nombre
            </label>
            <p className="rounded-lg bg-gray-50 px-3 py-2 text-sm font-medium dark:bg-gray-800" style={{ color: "hsl(var(--foreground))" }}>
              {profile.first_name}
            </p>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Apellido
            </label>
            <p className="rounded-lg bg-gray-50 px-3 py-2 text-sm font-medium dark:bg-gray-800" style={{ color: "hsl(var(--foreground))" }}>
              {profile.last_name}
            </p>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Tipo de documento
            </label>
            <p className="rounded-lg bg-gray-50 px-3 py-2 text-sm font-medium dark:bg-gray-800" style={{ color: "hsl(var(--foreground))" }}>
              {profile.document_type}
            </p>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Número de documento
            </label>
            <p className="rounded-lg bg-gray-50 px-3 py-2 text-sm font-medium dark:bg-gray-800" style={{ color: "hsl(var(--foreground))" }}>
              {profile.document_number}
            </p>
          </div>
        </div>
      </div>

      {/* Editable fields */}
      <form onSubmit={handleSubmit} noValidate>
        <div className="rounded-xl border bg-white p-6 shadow-sm dark:bg-gray-900 dark:border-gray-700">
          <h2 className="mb-4 text-base font-medium" style={{ color: "hsl(var(--foreground))" }}>
            Información de contacto
          </h2>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            {/* Phone */}
            <div>
              <label
                htmlFor="phone"
                className="mb-1.5 block text-sm font-medium"
                style={{ color: "hsl(var(--foreground))" }}
              >
                Teléfono
              </label>
              <input
                id="phone"
                name="phone"
                type="tel"
                value={form.phone}
                onChange={handleChange}
                placeholder="+57 300 000 0000"
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm outline-none transition-colors focus:border-cyan-600 focus:ring-2 focus:ring-cyan-600/20 dark:border-gray-700 dark:bg-gray-800 dark:focus:border-cyan-500"
                style={{ color: "hsl(var(--foreground))" }}
              />
            </div>

            {/* Email */}
            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-sm font-medium"
                style={{ color: "hsl(var(--foreground))" }}
              >
                Correo electrónico
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="correo@ejemplo.com"
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm outline-none transition-colors focus:border-cyan-600 focus:ring-2 focus:ring-cyan-600/20 dark:border-gray-700 dark:bg-gray-800 dark:focus:border-cyan-500"
                style={{ color: "hsl(var(--foreground))" }}
              />
            </div>

            {/* Address — full width */}
            <div className="sm:col-span-2">
              <label
                htmlFor="address"
                className="mb-1.5 block text-sm font-medium"
                style={{ color: "hsl(var(--foreground))" }}
              >
                Dirección
              </label>
              <input
                id="address"
                name="address"
                type="text"
                value={form.address}
                onChange={handleChange}
                placeholder="Calle 123 # 45-67, Bogotá"
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm outline-none transition-colors focus:border-cyan-600 focus:ring-2 focus:ring-cyan-600/20 dark:border-gray-700 dark:bg-gray-800 dark:focus:border-cyan-500"
                style={{ color: "hsl(var(--foreground))" }}
              />
            </div>
          </div>

          {/* Emergency contact section */}
          <div className="mt-6 border-t border-gray-100 pt-6 dark:border-gray-700">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Contacto de emergencia
            </h3>
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="emergency_contact_name"
                  className="mb-1.5 block text-sm font-medium"
                  style={{ color: "hsl(var(--foreground))" }}
                >
                  Nombre del contacto
                </label>
                <input
                  id="emergency_contact_name"
                  name="emergency_contact_name"
                  type="text"
                  value={form.emergency_contact_name}
                  onChange={handleChange}
                  placeholder="Nombre completo"
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm outline-none transition-colors focus:border-cyan-600 focus:ring-2 focus:ring-cyan-600/20 dark:border-gray-700 dark:bg-gray-800 dark:focus:border-cyan-500"
                  style={{ color: "hsl(var(--foreground))" }}
                />
              </div>

              <div>
                <label
                  htmlFor="emergency_contact_phone"
                  className="mb-1.5 block text-sm font-medium"
                  style={{ color: "hsl(var(--foreground))" }}
                >
                  Teléfono del contacto
                </label>
                <input
                  id="emergency_contact_phone"
                  name="emergency_contact_phone"
                  type="tel"
                  value={form.emergency_contact_phone}
                  onChange={handleChange}
                  placeholder="+57 300 000 0000"
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm outline-none transition-colors focus:border-cyan-600 focus:ring-2 focus:ring-cyan-600/20 dark:border-gray-700 dark:bg-gray-800 dark:focus:border-cyan-500"
                  style={{ color: "hsl(var(--foreground))" }}
                />
              </div>
            </div>
          </div>

          {/* Submit */}
          <div className="mt-6 flex justify-end">
            <button
              type="submit"
              disabled={isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-cyan-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-cyan-700 focus:outline-none focus:ring-2 focus:ring-cyan-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isPending ? "Guardando..." : "Guardar cambios"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
