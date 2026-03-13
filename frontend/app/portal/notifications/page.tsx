"use client";

import { usePortalNotificationPrefs, usePortalUpdateNotificationPrefs } from "@/lib/hooks/use-portal";
import { toast } from "sonner";

type PrefKey =
  | "email_enabled"
  | "whatsapp_enabled"
  | "sms_enabled"
  | "appointment_reminders"
  | "treatment_updates"
  | "billing_notifications"
  | "marketing_messages";

const CHANNELS: { key: PrefKey; label: string }[] = [
  { key: "email_enabled", label: "Correo electrónico" },
  { key: "whatsapp_enabled", label: "WhatsApp" },
  { key: "sms_enabled", label: "SMS" },
];

const NOTIFICATION_TYPES: { key: PrefKey; label: string }[] = [
  { key: "appointment_reminders", label: "Recordatorios de citas" },
  { key: "treatment_updates", label: "Actualizaciones de tratamiento" },
  { key: "billing_notifications", label: "Notificaciones de pagos" },
  { key: "marketing_messages", label: "Mensajes promocionales" },
];

function Toggle({ active, onToggle }: { active: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={active}
      onClick={onToggle}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary-600 ${
        active ? "bg-primary-600" : "bg-gray-300 dark:bg-gray-600"
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-lg transform transition-transform duration-200 ease-in-out ${
          active ? "translate-x-5" : "translate-x-0"
        }`}
      />
    </button>
  );
}

function PreferenceSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {[0, 1].map((section) => (
        <div
          key={section}
          className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6"
        >
          <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded mb-4" />
          <div className="space-y-4">
            {[0, 1, 2].map((row) => (
              <div key={row} className="flex items-center justify-between">
                <div className="h-4 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-6 w-11 bg-gray-200 dark:bg-gray-700 rounded-full" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function PreferenceSection({
  title,
  items,
  prefs,
  onToggle,
}: {
  title: string;
  items: { key: PrefKey; label: string }[];
  prefs: Record<PrefKey, boolean>;
  onToggle: (key: PrefKey, value: boolean) => void;
}) {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
        {title}
      </h2>
      <ul className="divide-y divide-gray-100 dark:divide-gray-800">
        {items.map(({ key, label }) => {
          const active = Boolean(prefs[key]);
          return (
            <li key={key} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
              <span className="text-sm font-medium text-[hsl(var(--foreground))]">{label}</span>
              <Toggle
                active={active}
                onToggle={() => onToggle(key, !active)}
              />
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function NotificationPreferencesPage() {
  const { data, isLoading, isError, refetch } = usePortalNotificationPrefs();
  const updateMutation = usePortalUpdateNotificationPrefs();

  const handleToggle = (key: PrefKey, value: boolean) => {
    updateMutation.mutate(
      { [key]: value },
      {
        onSuccess: () => {
          toast.success("Preferencia actualizada");
        },
        onError: () => {
          toast.error("No se pudo actualizar la preferencia. Intenta de nuevo.");
        },
      }
    );
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[hsl(var(--foreground))]">
          Preferencias de notificaciones
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Elige cómo quieres recibir tus notificaciones
        </p>
      </div>

      {isLoading && <PreferenceSkeleton />}

      {isError && !isLoading && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-8 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            No se pudieron cargar tus preferencias. Por favor, intenta de nuevo.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium bg-primary-600 text-white hover:bg-primary-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2"
          >
            Reintentar
          </button>
        </div>
      )}

      {!isLoading && !isError && data && (
        <div className="space-y-6">
          <PreferenceSection
            title="Canales"
            items={CHANNELS}
            prefs={data as Record<PrefKey, boolean>}
            onToggle={handleToggle}
          />
          <PreferenceSection
            title="Tipos de notificación"
            items={NOTIFICATION_TYPES}
            prefs={data as Record<PrefKey, boolean>}
            onToggle={handleToggle}
          />
        </div>
      )}
    </div>
  );
}
