"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Users, Plus, UserPlus, AlertCircle } from "lucide-react";
import { formatCurrency } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface FamilyMember {
  patient_id: string;
  patient_name: string;
  relationship: string;
  is_active: boolean;
}

interface FamilyGroup {
  id: string;
  name: string;
  primary_contact_patient_id: string;
  members: FamilyMember[];
}

interface FamilyBillingMember {
  patient_id: string;
  patient_name: string;
  total_billed: number;
  total_paid: number;
  total_balance: number;
}

interface FamilyBillingSummary {
  family_id: string;
  members: FamilyBillingMember[];
  total_billed: number;
  total_paid: number;
  total_balance: number;
}

// ─── Relationship Labels ──────────────────────────────────────────────────────

const RELATIONSHIP_OPTIONS = [
  { value: "spouse", label: "Cónyuge" },
  { value: "child", label: "Hijo/a" },
  { value: "parent", label: "Padre/Madre" },
  { value: "sibling", label: "Hermano/a" },
  { value: "grandparent", label: "Abuelo/a" },
  { value: "grandchild", label: "Nieto/a" },
  { value: "other", label: "Otro" },
];

function relationshipLabel(value: string): string {
  return RELATIONSHIP_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

// ─── Add Member Dialog ────────────────────────────────────────────────────────

function AddMemberDialog({
  familyId,
  open,
  onClose,
}: {
  familyId: string;
  open: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [patientId, setPatientId] = React.useState("");
  const [relationship, setRelationship] = React.useState("spouse");

  const { mutate: addMember, isPending } = useMutation({
    mutationFn: (payload: { patient_id: string; relationship: string }) =>
      apiPost(`/families/${familyId}/members`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["family"] });
      setPatientId("");
      setRelationship("spouse");
      onClose();
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!patientId.trim()) return;
    addMember({ patient_id: patientId.trim(), relationship });
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Agregar miembro al grupo familiar</DialogTitle>
          <DialogDescription>
            Busca al paciente por ID y selecciona su parentesco con el titular.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="patient-id">ID del paciente</Label>
            <Input
              id="patient-id"
              placeholder="UUID del paciente..."
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="relationship">Parentesco</Label>
            <select
              id="relationship"
              value={relationship}
              onChange={(e) => setRelationship(e.target.value)}
              className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary-600"
            >
              {RELATIONSHIP_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending || !patientId.trim()}>
              {isPending ? "Agregando..." : "Agregar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Create Family Dialog ─────────────────────────────────────────────────────

function CreateFamilyDialog({
  patientId,
  open,
  onClose,
}: {
  patientId: string;
  open: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [familyName, setFamilyName] = React.useState("");

  const { mutate: createFamily, isPending } = useMutation({
    mutationFn: (payload: { name: string; primary_contact_patient_id: string }) =>
      apiPost<FamilyGroup>("/families", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["family"] });
      setFamilyName("");
      onClose();
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!familyName.trim()) return;
    createFamily({ name: familyName.trim(), primary_contact_patient_id: patientId });
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Crear grupo familiar</DialogTitle>
          <DialogDescription>
            El paciente actual será el titular del grupo familiar.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="family-name">Nombre del grupo</Label>
            <Input
              id="family-name"
              placeholder="Ej: Familia García"
              value={familyName}
              onChange={(e) => setFamilyName(e.target.value)}
              required
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending || !familyName.trim()}>
              {isPending ? "Creando..." : "Crear grupo"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PatientFamilyPage() {
  const params = useParams<{ id: string }>();
  const patientId = params?.id ?? "";

  const [addMemberOpen, setAddMemberOpen] = React.useState(false);
  const [createFamilyOpen, setCreateFamilyOpen] = React.useState(false);

  const { data: family, isLoading: isLoadingFamily, isError: isFamilyError } = useQuery({
    queryKey: ["family", "patient", patientId],
    queryFn: () =>
      apiGet<FamilyGroup | null>(`/patients/${patientId}/family`).catch(() => null),
    enabled: !!patientId,
    staleTime: 30_000,
  });

  const { data: billing, isLoading: isLoadingBilling } = useQuery({
    queryKey: ["family", family?.id, "billing"],
    queryFn: () => apiGet<FamilyBillingSummary>(`/families/${family!.id}/billing`),
    enabled: !!family?.id,
    staleTime: 30_000,
  });

  const isLoading = isLoadingFamily || (!!family && isLoadingBilling);

  // ─── Loading ─────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
      </div>
    );
  }

  // ─── No family ───────────────────────────────────────────────────────────
  if (!family) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Grupo familiar
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Gestiona el grupo familiar del paciente y la facturación consolidada.
          </p>
        </div>

        <Card>
          <CardContent className="py-14">
            <div className="flex flex-col items-center gap-4 text-center">
              <Users className="h-12 w-12 text-[hsl(var(--muted-foreground))]" />
              <div>
                <p className="text-sm font-medium text-foreground">
                  Este paciente no tiene grupo familiar
                </p>
                <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
                  Crea un grupo familiar para vincular miembros y ver la facturación consolidada.
                </p>
              </div>
              <Button onClick={() => setCreateFamilyOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Crear grupo familiar
              </Button>
            </div>
          </CardContent>
        </Card>

        {isFamilyError && (
          <Card>
            <CardContent className="py-8 flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-500 shrink-0" />
              <p className="text-sm text-red-600 dark:text-red-400">
                Error al consultar el grupo familiar.
              </p>
            </CardContent>
          </Card>
        )}

        <CreateFamilyDialog
          patientId={patientId}
          open={createFamilyOpen}
          onClose={() => setCreateFamilyOpen(false)}
        />
      </div>
    );
  }

  // ─── Has family ──────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            {family.name}
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            {family.members.length} miembro{family.members.length !== 1 ? "s" : ""} en el grupo familiar
          </p>
        </div>
        <Button onClick={() => setAddMemberOpen(true)}>
          <UserPlus className="mr-2 h-4 w-4" />
          Agregar miembro
        </Button>
      </div>

      {/* ─── Members List ────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="h-4 w-4 text-primary-600" />
            Miembros del grupo
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead>
                <TableHead>Parentesco</TableHead>
                <TableHead>Rol</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {family.members.map((member) => (
                <TableRow key={member.patient_id}>
                  <TableCell className="font-medium text-foreground">
                    {member.patient_name}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">
                      {relationshipLabel(member.relationship)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {String(member.patient_id) === String(family.primary_contact_patient_id) ? (
                      <Badge variant="default">Titular</Badge>
                    ) : (
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">
                        Miembro
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* ─── Billing Summary ─────────────────────────────────────────────── */}
      {billing && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Resumen de facturación familiar</CardTitle>
            <CardDescription>
              Consolidado de saldos por miembro del grupo.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Paciente</TableHead>
                  <TableHead className="text-right">Total facturado</TableHead>
                  <TableHead className="text-right">Total pagado</TableHead>
                  <TableHead className="text-right">Saldo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {billing.members.map((m) => (
                  <TableRow key={m.patient_id}>
                    <TableCell className="font-medium text-foreground">
                      {m.patient_name}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm">
                      {formatCurrency(m.total_billed)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm text-green-600 dark:text-green-400">
                      {formatCurrency(m.total_paid)}
                    </TableCell>
                    <TableCell
                      className={`text-right tabular-nums text-sm font-semibold ${
                        m.total_balance > 0
                          ? "text-red-600 dark:text-red-400"
                          : "text-foreground"
                      }`}
                    >
                      {formatCurrency(m.total_balance)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
              <TableFooter>
                <TableRow className="bg-[hsl(var(--muted))]/50 font-semibold">
                  <TableCell className="font-bold text-foreground">
                    Total grupo familiar
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatCurrency(billing.total_billed)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-green-600 dark:text-green-400">
                    {formatCurrency(billing.total_paid)}
                  </TableCell>
                  <TableCell
                    className={`text-right tabular-nums font-bold ${
                      billing.total_balance > 0
                        ? "text-red-600 dark:text-red-400"
                        : "text-foreground"
                    }`}
                  >
                    {formatCurrency(billing.total_balance)}
                  </TableCell>
                </TableRow>
              </TableFooter>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* ─── Dialogs ─────────────────────────────────────────────────────── */}
      <AddMemberDialog
        familyId={family.id}
        open={addMemberOpen}
        onClose={() => setAddMemberOpen(false)}
      />
    </div>
  );
}
