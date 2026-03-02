import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge } from "../badge";

describe("Badge", () => {
  it("renders with text", () => {
    render(<Badge>Activo</Badge>);
    expect(screen.getByText("Activo")).toBeInTheDocument();
  });

  it("applies variant classes", () => {
    render(<Badge variant="success">Completado</Badge>);
    const badge = screen.getByText("Completado");
    expect(badge.className).toContain("success");
  });

  it("applies custom className", () => {
    render(<Badge className="ml-2">Test</Badge>);
    expect(screen.getByText("Test").className).toContain("ml-2");
  });
});
