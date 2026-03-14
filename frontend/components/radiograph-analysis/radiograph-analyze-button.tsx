"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useAnalyzeRadiograph } from "@/lib/hooks/use-radiograph-analysis";

interface RadiographAnalyzeButtonProps {
  patientId: string;
  documentId: string;
  radiographType?: string;
  disabled?: boolean;
}

export function RadiographAnalyzeButton({
  patientId,
  documentId,
  radiographType = "periapical",
  disabled = false,
}: RadiographAnalyzeButtonProps) {
  const [showTypeSelect, setShowTypeSelect] = useState(false);
  const [selectedType, setSelectedType] = useState(radiographType);
  const analyzeMutation = useAnalyzeRadiograph(patientId);

  const radiographTypes = [
    { value: "periapical", label: "Periapical" },
    { value: "bitewing", label: "Bitewing" },
    { value: "panoramic", label: "Panorámica" },
    { value: "cephalometric", label: "Cefalométrica" },
    { value: "occlusal", label: "Oclusal" },
  ];

  const handleAnalyze = async () => {
    try {
      await analyzeMutation.mutateAsync({
        document_id: documentId,
        radiograph_type: selectedType,
      });
      toast.success("Análisis de radiografía iniciado. Se procesará en unos segundos.");
      setShowTypeSelect(false);
    } catch (error: any) {
      if (error?.response?.status === 402) {
        toast.error(
          "El análisis de radiografías con IA requiere el add-on AI Radiograph ($20/doctor/mes).",
          { duration: 5000 },
        );
      } else if (error?.response?.status === 409) {
        toast.warning("Ya existe un análisis en proceso para este documento.");
      } else {
        toast.error("Error al iniciar el análisis de radiografía.");
      }
    }
  };

  if (showTypeSelect) {
    return (
      <div className="flex items-center gap-2">
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
        >
          {radiographTypes.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
        <button
          onClick={handleAnalyze}
          disabled={analyzeMutation.isPending}
          className="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {analyzeMutation.isPending ? "Analizando..." : "Confirmar"}
        </button>
        <button
          onClick={() => setShowTypeSelect(false)}
          className="rounded-md px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700"
        >
          Cancelar
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => setShowTypeSelect(true)}
      disabled={disabled || analyzeMutation.isPending}
      className="inline-flex items-center gap-1.5 rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
    >
      <svg
        className="h-4 w-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
        />
      </svg>
      Analizar con IA
    </button>
  );
}
