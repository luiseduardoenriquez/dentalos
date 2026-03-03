"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ClipboardCheck, ClipboardX } from "lucide-react";
import { cn } from "@/lib/utils";

interface IntakeStatusIndicatorProps {
  completed: boolean;
  completedAt?: string | null;
  className?: string;
}

export function IntakeStatusIndicator({
  completed,
  completedAt,
  className,
}: IntakeStatusIndicatorProps) {
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className={cn("inline-flex", className)}>
            {completed ? (
              <Badge variant="success" className="gap-1 text-xs">
                <ClipboardCheck className="h-3 w-3" />
                Formulario
              </Badge>
            ) : (
              <Badge
                variant="outline"
                className="gap-1 text-xs text-[hsl(var(--muted-foreground))]"
              >
                <ClipboardX className="h-3 w-3" />
                Pendiente
              </Badge>
            )}
          </span>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          {completed
            ? `Formulario de ingreso completado${
                completedAt
                  ? ` el ${new Date(completedAt).toLocaleDateString("es-CO")}`
                  : ""
              }`
            : "El paciente aún no ha completado el formulario de ingreso"}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
