"use client";

import * as React from "react";
import { useAuditTrail, type AuditLogEntry } from "@/lib/hooks/use-analytics";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RefreshCw, ChevronDown, ChevronRight, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/hooks/use-auth";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString("es-CO", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

const RESOURCE_TYPE_OPTIONS = [
  { value: "", label: "Todos los recursos" },
  { value: "patient", label: "Paciente" },
  { value: "appointment", label: "Cita" },
  { value: "clinical_record", label: "Registro clínico" },
  { value: "treatment_plan", label: "Plan de tratamiento" },
  { value: "invoice", label: "Factura" },
  { value: "consent", label: "Consentimiento" },
  { value: "user", label: "Usuario" },
  { value: "tenant", label: "Tenant" },
];

const ACTION_OPTIONS = [
  { value: "", label: "Todas las acciones" },
  { value: "create", label: "Crear" },
  { value: "update", label: "Actualizar" },
  { value: "delete", label: "Eliminar" },
  { value: "view", label: "Ver" },
  { value: "login", label: "Inicio de sesión" },
  { value: "logout", label: "Cierre de sesión" },
  { value: "export", label: "Exportar" },
];

// ─── Expandable Row ───────────────────────────────────────────────────────────

function AuditRow({ entry }: { entry: AuditLogEntry }) {
  const [expanded, setExpanded] = React.useState(false);
  const hasChanges = entry.changes && Object.keys(entry.changes).length > 0;

  return (
    <>
      <TableRow
        className={cn(hasChanges && "cursor-pointer hover:bg-[hsl(var(--muted))]/50")}
        onClick={() => hasChanges && setExpanded((v) => !v)}
      >
        <TableCell className="tabular-nums text-xs whitespace-nowrap">
          {formatDateTime(entry.created_at)}
        </TableCell>
        <TableCell className="text-sm">
          {entry.user_name ?? (
            <span className="text-[hsl(var(--muted-foreground))] italic">
              Desconocido
            </span>
          )}
        </TableCell>
        <TableCell>
          <span className="rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 px-2 py-0.5 text-xs font-medium">
            {entry.action}
          </span>
        </TableCell>
        <TableCell className="text-sm">
          {entry.resource_type}
        </TableCell>
        <TableCell className="font-mono text-xs text-[hsl(var(--muted-foreground))] truncate max-w-[140px]">
          {entry.resource_id ?? "—"}
        </TableCell>
        <TableCell className="text-xs text-[hsl(var(--muted-foreground))]">
          {entry.ip_address ?? "—"}
        </TableCell>
        <TableCell className="w-8">
          {hasChanges && (
            <span className="text-[hsl(var(--muted-foreground))]">
              {expanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </span>
          )}
        </TableCell>
      </TableRow>

      {/* Expanded changes detail */}
      {expanded && hasChanges && (
        <TableRow>
          <TableCell colSpan={7} className="bg-[hsl(var(--muted))]/30 p-0">
            <div className="px-4 py-3">
              <p className="text-xs font-semibold text-[hsl(var(--muted-foreground))] mb-2 uppercase tracking-wide">
                Cambios registrados
              </p>
              <pre className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-3 text-xs overflow-x-auto">
                {JSON.stringify(entry.changes, null, 2)}
              </pre>
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AuditLogPage() {
  const { has_role } = useAuth();
  const isOwner = has_role("clinic_owner");

  // Filter state
  const [userSearch, setUserSearch] = React.useState("");
  const [resourceType, setResourceType] = React.useState("");
  const [action, setAction] = React.useState("");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");

  // Applied filters (only sent to API when user presses "Aplicar")
  const [appliedFilters, setAppliedFilters] = React.useState({
    userSearch: "",
    resourceType: "",
    action: "",
    dateFrom: "",
    dateTo: "",
  });

  // Cursor-based pagination: accumulated pages
  const [cursors, setCursors] = React.useState<(string | undefined)[]>([
    undefined,
  ]);
  const currentCursor = cursors[cursors.length - 1];

  const { data, isLoading, isError } = useAuditTrail(
    currentCursor,
    appliedFilters.userSearch || undefined,
    appliedFilters.resourceType || undefined,
    appliedFilters.action || undefined,
    appliedFilters.dateFrom || undefined,
    appliedFilters.dateTo || undefined,
  );

  // Accumulated items across pages
  const [allItems, setAllItems] = React.useState<AuditLogEntry[]>([]);

  React.useEffect(() => {
    if (!data) return;
    if (cursors.length === 1) {
      // First page — replace
      setAllItems(data.items);
    } else {
      // Subsequent pages — append
      setAllItems((prev) => [...prev, ...data.items]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  function handleApplyFilters() {
    // Reset pagination on new filter
    setCursors([undefined]);
    setAllItems([]);
    setAppliedFilters({
      userSearch,
      resourceType,
      action,
      dateFrom,
      dateTo,
    });
  }

  function handleClearFilters() {
    setUserSearch("");
    setResourceType("");
    setAction("");
    setDateFrom("");
    setDateTo("");
    setCursors([undefined]);
    setAllItems([]);
    setAppliedFilters({
      userSearch: "",
      resourceType: "",
      action: "",
      dateFrom: "",
      dateTo: "",
    });
  }

  function handleLoadMore() {
    if (data?.next_cursor) {
      setCursors((prev) => [...prev, data.next_cursor!]);
    }
  }

  if (!isOwner) {
    return (
      <div className="max-w-3xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Registro de auditoría
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            Historial completo de acciones realizadas en la clínica.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
          <Lock className="h-4 w-4 shrink-0" />
          Solo el propietario de la clínica puede ver el registro de auditoría.
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Registro de auditoría
        </h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Historial completo de acciones realizadas en la clínica.
        </p>
      </div>

      {/* Filter controls */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Filtros</CardTitle>
          <CardDescription>
            Filtra por usuario, tipo de recurso, acción o rango de fechas.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {/* User search */}
            <div className="space-y-1">
              <label
                htmlFor="user-search"
                className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
              >
                Usuario (nombre o ID)
              </label>
              <Input
                id="user-search"
                placeholder="Buscar usuario..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
              />
            </div>

            {/* Resource type */}
            <div className="space-y-1">
              <label
                htmlFor="resource-type"
                className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
              >
                Tipo de recurso
              </label>
              <select
                id="resource-type"
                value={resourceType}
                onChange={(e) => setResourceType(e.target.value)}
                className={cn(
                  "w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
                  "px-3 py-2 text-sm text-foreground shadow-sm",
                  "focus:outline-none focus:ring-2 focus:ring-primary-600",
                )}
              >
                {RESOURCE_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Action */}
            <div className="space-y-1">
              <label
                htmlFor="action-filter"
                className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
              >
                Acción
              </label>
              <select
                id="action-filter"
                value={action}
                onChange={(e) => setAction(e.target.value)}
                className={cn(
                  "w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
                  "px-3 py-2 text-sm text-foreground shadow-sm",
                  "focus:outline-none focus:ring-2 focus:ring-primary-600",
                )}
              >
                {ACTION_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Date from */}
            <div className="space-y-1">
              <label
                htmlFor="date-from"
                className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
              >
                Desde
              </label>
              <Input
                id="date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>

            {/* Date to */}
            <div className="space-y-1">
              <label
                htmlFor="date-to"
                className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
              >
                Hasta
              </label>
              <Input
                id="date-to"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>

            {/* Actions */}
            <div className="flex items-end gap-2">
              <Button onClick={handleApplyFilters} className="flex-1">
                Aplicar filtros
              </Button>
              <Button variant="outline" onClick={handleClearFilters}>
                Limpiar
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Data table */}
      <Card>
        <CardHeader>
          <CardTitle>Eventos de auditoría</CardTitle>
          <CardDescription>
            Haz clic en una fila para ver los cambios detallados.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading && cursors.length === 1 ? (
            <div className="flex items-center justify-center py-16">
              <RefreshCw className="h-6 w-6 animate-spin text-[hsl(var(--muted-foreground))]" />
            </div>
          ) : isError ? (
            <p className="py-10 text-center text-sm text-[hsl(var(--muted-foreground))]">
              No se pudo cargar el registro. Intenta de nuevo.
            </p>
          ) : allItems.length === 0 ? (
            <p className="py-10 text-center text-sm text-[hsl(var(--muted-foreground))]">
              No hay eventos que coincidan con los filtros aplicados.
            </p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Fecha y hora</TableHead>
                      <TableHead>Usuario</TableHead>
                      <TableHead>Acción</TableHead>
                      <TableHead>Recurso</TableHead>
                      <TableHead>ID recurso</TableHead>
                      <TableHead>IP</TableHead>
                      <TableHead className="w-8" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {allItems.map((entry) => (
                      <AuditRow key={entry.id} entry={entry} />
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Load more */}
              {data?.has_more && (
                <div className="flex justify-center border-t border-[hsl(var(--border))] p-4">
                  <Button
                    variant="outline"
                    onClick={handleLoadMore}
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <>
                        <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                        Cargando...
                      </>
                    ) : (
                      "Cargar más"
                    )}
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
