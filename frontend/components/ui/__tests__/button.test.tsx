import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button } from "../button";

describe("Button", () => {
  it("renders with text", () => {
    render(<Button>Guardar</Button>);
    expect(screen.getByRole("button", { name: "Guardar" })).toBeInTheDocument();
  });

  it("applies variant classes", () => {
    render(<Button variant="destructive">Eliminar</Button>);
    const btn = screen.getByRole("button", { name: "Eliminar" });
    expect(btn.className).toContain("destructive");
  });

  it("passes disabled attribute", () => {
    render(<Button disabled>Guardar</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
