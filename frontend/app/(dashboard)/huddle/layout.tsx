import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Resumen del Día | DentalOS",
};

export default function HuddleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
