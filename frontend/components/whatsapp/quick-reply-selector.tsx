"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Zap } from "lucide-react";
import { apiGet } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface QuickReply {
  id: string;
  title: string;
  body: string;
  category: string;
  shortcut: string | null;
  is_active: boolean;
}

interface QuickReplyListResponse {
  items: QuickReply[];
  total: number;
}

interface QuickReplySelectorProps {
  onSelect: (body: string) => void;
}

// ─── Query Key ────────────────────────────────────────────────────────────────

const QUICK_REPLIES_KEY = ["quick-replies"] as const;

// ─── QuickReplySelector ───────────────────────────────────────────────────────

export function QuickReplySelector({ onSelect }: QuickReplySelectorProps) {
  const { data, isLoading } = useQuery({
    queryKey: QUICK_REPLIES_KEY,
    queryFn: () => apiGet<QuickReplyListResponse>("/messaging/quick-replies"),
    staleTime: 5 * 60_000, // 5 minutes
  });

  // Group by category
  const grouped = React.useMemo(() => {
    if (!data?.items) return {} as Record<string, QuickReply[]>;
    return data.items
      .filter((r) => r.is_active)
      .reduce<Record<string, QuickReply[]>>((acc, reply) => {
        const cat = reply.category || "General";
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(reply);
        return acc;
      }, {});
  }, [data?.items]);

  const categories = Object.keys(grouped).sort();
  const hasReplies = categories.length > 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5 h-8"
          disabled={isLoading}
          aria-label="Respuestas rápidas"
        >
          <Zap className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Respuesta rápida</span>
          <ChevronDown className="h-3.5 w-3.5 opacity-60" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align="start"
        side="top"
        className="w-72 max-h-80 overflow-y-auto"
      >
        {isLoading && (
          <div className="py-3 px-4 text-sm text-[hsl(var(--muted-foreground))]">
            Cargando respuestas...
          </div>
        )}

        {!isLoading && !hasReplies && (
          <div className="py-3 px-4 text-sm text-[hsl(var(--muted-foreground))]">
            Sin respuestas rápidas configuradas.
          </div>
        )}

        {!isLoading &&
          hasReplies &&
          categories.map((category, idx) => (
            <React.Fragment key={category}>
              {idx > 0 && <DropdownMenuSeparator />}
              <DropdownMenuGroup>
                <DropdownMenuLabel className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] px-3 py-1.5">
                  {category}
                </DropdownMenuLabel>
                {grouped[category].map((reply) => (
                  <DropdownMenuItem
                    key={reply.id}
                    onSelect={() => onSelect(reply.body)}
                    className={cn(
                      "flex flex-col items-start gap-0.5 px-3 py-2 cursor-pointer",
                    )}
                  >
                    <span className="text-sm font-medium">{reply.title}</span>
                    <span className="text-xs text-[hsl(var(--muted-foreground))] line-clamp-2">
                      {reply.body}
                    </span>
                    {reply.shortcut && (
                      <span className="text-[10px] text-primary-600 dark:text-primary-400 font-mono">
                        /{reply.shortcut}
                      </span>
                    )}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuGroup>
            </React.Fragment>
          ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
