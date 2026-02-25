"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SignaturePadProps {
  onSignature: (base64Png: string) => void;
  onClear?: () => void;
  width?: number;
  height?: number;
  disabled?: boolean;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function SignaturePad({
  onSignature,
  onClear,
  height = 180,
  disabled = false,
  className,
}: SignaturePadProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawingRef = useRef(false);
  const lastPosRef = useRef<{ x: number; y: number } | null>(null);
  const [isEmpty, setIsEmpty] = useState(true);

  // ── Canvas setup ──────────────────────────────────────────────────

  const setupCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Match canvas pixel size to its CSS display size for sharp rendering
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.scale(dpr, dpr);
    ctx.strokeStyle = "#1e293b"; // slate-800
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Draw placeholder text when empty
    drawPlaceholder(ctx, rect.width, rect.height);
  }, []);

  function drawPlaceholder(
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number,
  ) {
    ctx.clearRect(0, 0, width, height);
    ctx.font = "14px system-ui, sans-serif";
    ctx.fillStyle = "#94a3b8"; // slate-400
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("Firme aquí", width / 2, height / 2);
  }

  useEffect(() => {
    setupCanvas();

    const handleResize = () => {
      // Re-setup on resize (canvas dimensions must match CSS dimensions)
      const wasEmpty = isEmpty;
      setupCanvas();
      if (!wasEmpty) {
        // If there was a signature, clear it — resize invalidates the drawing
        setIsEmpty(true);
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setupCanvas]);

  // ── Coordinate helpers ────────────────────────────────────────────

  function getCanvasCoords(
    canvas: HTMLCanvasElement,
    clientX: number,
    clientY: number,
  ): { x: number; y: number } {
    const rect = canvas.getBoundingClientRect();
    return {
      x: clientX - rect.left,
      y: clientY - rect.top,
    };
  }

  // ── Drawing logic ─────────────────────────────────────────────────

  function startDraw(x: number, y: number) {
    if (disabled) return;

    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    isDrawingRef.current = true;

    // Clear placeholder on first stroke
    if (isEmpty) {
      ctx.clearRect(0, 0, canvas.getBoundingClientRect().width, canvas.getBoundingClientRect().height);
      setIsEmpty(false);
    }

    lastPosRef.current = { x, y };

    // Draw a dot for single taps/clicks
    ctx.beginPath();
    ctx.arc(x, y, 1, 0, Math.PI * 2);
    ctx.fillStyle = "#1e293b";
    ctx.fill();
  }

  function draw(x: number, y: number) {
    if (!isDrawingRef.current || disabled) return;

    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx || !lastPosRef.current) return;

    ctx.beginPath();
    ctx.moveTo(lastPosRef.current.x, lastPosRef.current.y);
    ctx.lineTo(x, y);
    ctx.stroke();

    lastPosRef.current = { x, y };
  }

  function endDraw() {
    isDrawingRef.current = false;
    lastPosRef.current = null;
  }

  // ── Mouse event handlers ──────────────────────────────────────────

  function handleMouseDown(e: React.MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const { x, y } = getCanvasCoords(canvas, e.clientX, e.clientY);
    startDraw(x, y);
  }

  function handleMouseMove(e: React.MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const { x, y } = getCanvasCoords(canvas, e.clientX, e.clientY);
    draw(x, y);
  }

  function handleMouseUp() {
    endDraw();
  }

  function handleMouseLeave() {
    endDraw();
  }

  // ── Touch event handlers ──────────────────────────────────────────

  function handleTouchStart(e: React.TouchEvent<HTMLCanvasElement>) {
    // Prevent page scroll while drawing
    e.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas || e.touches.length === 0) return;
    const touch = e.touches[0];
    const { x, y } = getCanvasCoords(canvas, touch.clientX, touch.clientY);
    startDraw(x, y);
  }

  function handleTouchMove(e: React.TouchEvent<HTMLCanvasElement>) {
    // Prevent page scroll while drawing
    e.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas || e.touches.length === 0) return;
    const touch = e.touches[0];
    const { x, y } = getCanvasCoords(canvas, touch.clientX, touch.clientY);
    draw(x, y);
  }

  function handleTouchEnd(e: React.TouchEvent<HTMLCanvasElement>) {
    e.preventDefault();
    endDraw();
  }

  // ── Actions ───────────────────────────────────────────────────────

  function handleClear() {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const rect = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, rect.width, rect.height);
    drawPlaceholder(ctx, rect.width, rect.height);
    setIsEmpty(true);
    onClear?.();
  }

  function handleConfirm() {
    const canvas = canvasRef.current;
    if (!canvas || isEmpty) return;

    // Export as PNG, strip the data URL prefix
    const dataUrl = canvas.toDataURL("image/png");
    const base64 = dataUrl.replace(/^data:image\/png;base64,/, "");
    onSignature(base64);
  }

  // ── Render ────────────────────────────────────────────────────────

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {/* Canvas area */}
      <div
        className={cn(
          "relative w-full overflow-hidden rounded-lg border-2 border-dashed bg-[hsl(var(--muted)/0.3)]",
          disabled
            ? "cursor-not-allowed border-[hsl(var(--border))] opacity-60"
            : "cursor-crosshair border-[hsl(var(--border))] hover:border-primary-400 transition-colors",
        )}
        style={{ height }}
      >
        <canvas
          ref={canvasRef}
          className="absolute inset-0 h-full w-full touch-none"
          style={{ cursor: disabled ? "not-allowed" : "crosshair" }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          aria-label="Área de firma"
        />
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-between gap-3">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleClear}
          disabled={disabled || isEmpty}
          className="min-w-[90px]"
        >
          Limpiar
        </Button>

        <Button
          type="button"
          size="sm"
          onClick={handleConfirm}
          disabled={disabled || isEmpty}
          className="min-w-[120px]"
        >
          Firmar
        </Button>
      </div>
    </div>
  );
}
