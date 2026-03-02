import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Input } from "../input";

describe("Input", () => {
  it("renders with placeholder", () => {
    render(<Input placeholder="Buscar paciente..." />);
    expect(screen.getByPlaceholderText("Buscar paciente...")).toBeInTheDocument();
  });

  it("passes disabled attribute", () => {
    render(<Input disabled placeholder="test" />);
    expect(screen.getByPlaceholderText("test")).toBeDisabled();
  });

  it("renders with type", () => {
    render(<Input type="email" placeholder="correo" />);
    expect(screen.getByPlaceholderText("correo")).toHaveAttribute("type", "email");
  });
});
