"use client";

import * as React from "react";
import Link from "next/link";
import { ChevronRight, RefreshCw, Upload, FileText, RotateCcw, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  useStartImport,
  useImportStatus,
  type PatientImportJob,
} from "@/lib/hooks/use-patient-import";

// ─── Constants ────────────────────────────────────────────────────────────────

const CSV_TEMPLATE_HEADER =
  "tipo_documento,numero_documento,nombres,apellidos,fecha_nacimiento,genero,email,telefono,ciudad";

const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

// ─── Status Badge ─────────────────────────────────────────────────────────────

function ImportStatusBadge({ status }: { status: string }) {
  switch (status) {
    case "queued":
      return <Badge variant="warning">En cola</Badge>;
    case "processing":
      return (
        <Badge variant="default" className="gap-1.5">
          <RefreshCw className="h-3 w-3 animate-spin" />
          Procesando
        </Badge>
      );
    case "completed":
      return <Badge variant="success">Completado</Badge>;
    case "failed":
      return <Badge variant="destructive">Fallido</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
}

// ─── Progress Section ─────────────────────────────────────────────────────────

interface ProgressSectionProps {
  job: PatientImportJob;
  onReset: () => void;
}

function ProgressSection({ job, onReset }: ProgressSectionProps) {
  const isFinished = job.status === "completed" || job.status === "failed";
  const progressValue =
    job.total_rows > 0
      ? Math.round((job.processed_rows / job.total_rows) * 100)
      : 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <div>
            <CardTitle className="text-base">Estado de la importación</CardTitle>
            <CardDescription className="mt-1">
              ID del trabajo: <span className="font-mono text-xs">{job.job_id}</span>
            </CardDescription>
          </div>
          <ImportStatusBadge status={job.status} />
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* ─── Progress Bar ────────────────────────────────────────── */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[hsl(var(--muted-foreground))]">Progreso</span>
            <span className="font-medium tabular-nums">
              {job.processed_rows} / {job.total_rows} filas ({progressValue}%)
            </span>
          </div>
          <Progress value={progressValue} />
        </div>

        {/* ─── Stats Grid ──────────────────────────────────────────── */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Total" value={job.total_rows} />
          <StatCard label="Exitosos" value={job.success_count} variant="success" />
          <StatCard label="Errores" value={job.error_count} variant="error" />
          <StatCard label="Duplicados" value={job.duplicate_count} variant="warning" />
        </div>

        {/* ─── Error File Download ──────────────────────────────────── */}
        {isFinished && job.error_file_url && job.error_count > 0 && (
          <div className="flex items-center gap-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-4 py-3">
            <FileText className="h-4 w-4 shrink-0 text-[hsl(var(--muted-foreground))]" />
            <p className="flex-1 text-sm text-[hsl(var(--muted-foreground))]">
              Se encontraron {job.error_count} filas con errores.
            </p>
            <Button variant="outline" size="sm" asChild>
              <a href={job.error_file_url} download>
                <Download className="mr-1.5 h-3.5 w-3.5" />
                Descargar errores
              </a>
            </Button>
          </div>
        )}

        {/* ─── Reset Button ────────────────────────────────────────── */}
        {isFinished && (
          <div className="flex justify-end">
            <Button variant="outline" onClick={onReset}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Nueva importación
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: number;
  variant?: "default" | "success" | "error" | "warning";
}

function StatCard({ label, value, variant = "default" }: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-md border px-3 py-3 text-center",
        variant === "success" &&
          "border-success-500/30 bg-success-50 dark:bg-success-700/10",
        variant === "error" &&
          "border-destructive-200 bg-destructive-50 dark:bg-destructive-900/20",
        variant === "warning" &&
          "border-accent-500/30 bg-warning-50 dark:bg-accent-700/10",
        variant === "default" && "border-[hsl(var(--border))] bg-[hsl(var(--muted))]",
      )}
    >
      <p
        className={cn(
          "text-2xl font-bold tabular-nums",
          variant === "success" && "text-success-700 dark:text-success-300",
          variant === "error" && "text-destructive-700 dark:text-destructive-300",
          variant === "warning" && "text-accent-700 dark:text-accent-300",
          variant === "default" && "text-foreground",
        )}
      >
        {value.toLocaleString("es-CO")}
      </p>
      <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">{label}</p>
    </div>
  );
}

// ─── Upload Section ───────────────────────────────────────────────────────────

interface UploadSectionProps {
  onJobStarted: (jobId: string) => void;
}

function UploadSection({ onJobStarted }: UploadSectionProps) {
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [fileError, setFileError] = React.useState<string | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const { mutate: startImport, isPending } = useStartImport();

  // ─── File selection handler ──────────────────────────────────────
  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setFileError(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!file.name.endsWith(".csv")) {
      setFileError("Solo se permiten archivos CSV (.csv).");
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setFileError("El archivo no puede superar 5 MB.");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  }

  // ─── Drag & drop handlers ────────────────────────────────────────
  const [isDragOver, setIsDragOver] = React.useState(false);

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave() {
    setIsDragOver(false);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragOver(false);
    setFileError(null);

    const file = e.dataTransfer.files?.[0] ?? null;
    if (!file) return;

    if (!file.name.endsWith(".csv")) {
      setFileError("Solo se permiten archivos CSV (.csv).");
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setFileError("El archivo no puede superar 5 MB.");
      return;
    }

    setSelectedFile(file);
  }

  // ─── Submit handler ──────────────────────────────────────────────
  function handleImport() {
    if (!selectedFile) return;

    startImport(selectedFile, {
      onSuccess: (resp) => {
        onJobStarted(resp.job_id);
      },
    });
  }

  // ─── Template download ───────────────────────────────────────────
  function handleDownloadTemplate() {
    const blob = new Blob([CSV_TEMPLATE_HEADER + "\n"], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "plantilla_pacientes.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Importar pacientes desde CSV</CardTitle>
        <CardDescription>
          Sube un archivo CSV con la información de los pacientes para importarlos en lote.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* ─── Dropzone ────────────────────────────────────────────── */}
        <div
          role="button"
          tabIndex={0}
          aria-label="Área para subir archivo CSV"
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
          }}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors",
            isDragOver
              ? "border-primary-500 bg-primary-50 dark:bg-primary-900/10"
              : "border-[hsl(var(--border))] hover:border-primary-400 hover:bg-[hsl(var(--muted))]",
            fileError && "border-destructive-400",
          )}
        >
          <Upload
            className={cn(
              "mb-3 h-8 w-8",
              isDragOver ? "text-primary-600" : "text-[hsl(var(--muted-foreground))]",
            )}
          />

          {selectedFile ? (
            <div className="space-y-1">
              <p className="font-medium text-foreground">{selectedFile.name}</p>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
              <p className="text-xs text-primary-600 dark:text-primary-400">
                Haz clic para cambiar el archivo
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              <p className="font-medium text-foreground">Seleccionar archivo CSV</p>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Arrastra aquí o haz clic para seleccionar · Máx. 5 MB
              </p>
            </div>
          )}
        </div>

        {/* Hidden file input */}
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={handleFileChange}
          aria-hidden="true"
        />

        {/* File error */}
        {fileError && (
          <p className="text-xs text-destructive-600 dark:text-destructive-400">{fileError}</p>
        )}

        {/* ─── Format hint ─────────────────────────────────────────── */}
        <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-4 py-3">
          <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed">
            <span className="font-semibold text-foreground">Formato requerido:</span>{" "}
            <span className="font-mono">
              tipo_documento, numero_documento, nombres, apellidos, fecha_nacimiento, genero, email,
              telefono, ciudad
            </span>
          </p>
        </div>

        {/* ─── Actions ─────────────────────────────────────────────── */}
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleDownloadTemplate}
          >
            <Download className="mr-2 h-3.5 w-3.5" />
            Descargar plantilla CSV
          </Button>

          <Button
            type="button"
            disabled={!selectedFile || isPending}
            onClick={handleImport}
          >
            {isPending ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                Iniciando importación...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Importar
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PatientImportPage() {
  const [jobId, setJobId] = React.useState<string | null>(null);

  const { data: job, isLoading: isJobLoading } = useImportStatus(jobId ?? "");

  function handleJobStarted(id: string) {
    setJobId(id);
  }

  function handleReset() {
    setJobId(null);
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* ─── Breadcrumb ────────────────────────────────────────────────── */}
      <nav
        className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
        aria-label="Ruta de navegación"
      >
        <Link href="/patients" className="hover:text-foreground transition-colors">
          Pacientes
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Importar pacientes</span>
      </nav>

      {/* ─── Page Title ────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Importar pacientes
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Importa pacientes en lote desde un archivo CSV.
        </p>
      </div>

      {/* ─── Upload Section (hidden while job is active) ──────────────── */}
      {!jobId && <UploadSection onJobStarted={handleJobStarted} />}

      {/* ─── Progress Section ──────────────────────────────────────────── */}
      {jobId && (
        <>
          {isJobLoading || !job ? (
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <RefreshCw className="h-6 w-6 animate-spin text-[hsl(var(--muted-foreground))]" />
              </CardContent>
            </Card>
          ) : (
            <ProgressSection job={job} onReset={handleReset} />
          )}
        </>
      )}
    </div>
  );
}
