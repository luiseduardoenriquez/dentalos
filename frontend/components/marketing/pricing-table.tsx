import { Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type CellValue = boolean | string;

interface FeatureRow {
  feature: string;
  gratis: CellValue;
  starter: CellValue;
  pro: CellValue;
  clinica: CellValue;
  enterprise: CellValue;
}

interface FeatureCategory {
  category: string;
  rows: FeatureRow[];
}

// ─── Comparison Data ──────────────────────────────────────────────────────────

const FEATURE_MATRIX: FeatureCategory[] = [
  {
    category: "Clinico",
    rows: [
      {
        feature: "Odontograma digital",
        gratis: true,
        starter: true,
        pro: true,
        clinica: true,
        enterprise: true,
      },
      {
        feature: "Historia clinica",
        gratis: false,
        starter: true,
        pro: true,
        clinica: true,
        enterprise: true,
      },
      {
        feature: "Plantillas de evolucion",
        gratis: false,
        starter: true,
        pro: true,
        clinica: true,
        enterprise: true,
      },
      {
        feature: "Consentimientos digitales",
        gratis: false,
        starter: true,
        pro: true,
        clinica: true,
        enterprise: true,
      },
      {
        feature: "Prescripciones",
        gratis: false,
        starter: true,
        pro: true,
        clinica: true,
        enterprise: true,
      },
    ],
  },
  {
    category: "Operativo",
    rows: [
      {
        feature: "Agenda",
        gratis: true,
        starter: true,
        pro: true,
        clinica: true,
        enterprise: true,
      },
      {
        feature: "Facturacion basica",
        gratis: false,
        starter: true,
        pro: true,
        clinica: true,
        enterprise: true,
      },
      {
        feature: "Portal del paciente",
        gratis: false,
        starter: false,
        pro: true,
        clinica: true,
        enterprise: true,
      },
      {
        feature: "Inventario",
        gratis: false,
        starter: false,
        pro: false,
        clinica: true,
        enterprise: true,
      },
      {
        feature: "Roles y permisos avanzados",
        gratis: false,
        starter: false,
        pro: false,
        clinica: true,
        enterprise: true,
      },
    ],
  },
  {
    category: "Cumplimiento",
    rows: [
      {
        feature: "RIPS automatico",
        gratis: false,
        starter: false,
        pro: true,
        clinica: true,
        enterprise: true,
      },
      {
        feature: "Facturacion DIAN electronica",
        gratis: false,
        starter: false,
        pro: true,
        clinica: true,
        enterprise: true,
      },
      {
        feature: "Firma digital legal",
        gratis: false,
        starter: false,
        pro: true,
        clinica: true,
        enterprise: true,
      },
    ],
  },
  {
    category: "Avanzado",
    rows: [
      {
        feature: "Reportes y analitica",
        gratis: false,
        starter: false,
        pro: true,
        clinica: true,
        enterprise: true,
      },
      {
        feature: "API de integracion",
        gratis: false,
        starter: false,
        pro: false,
        clinica: true,
        enterprise: true,
      },
      {
        feature: "Soporte 24/7",
        gratis: false,
        starter: false,
        pro: false,
        clinica: false,
        enterprise: true,
      },
      {
        feature: "Migracion dedicada",
        gratis: false,
        starter: false,
        pro: false,
        clinica: false,
        enterprise: true,
      },
    ],
  },
];

const PLAN_HEADERS = ["Gratis", "Starter", "Pro", "Clinica", "Enterprise"];

// ─── Cell Renderer ─────────────────────────────────────────────────────────────

function TableCell({ value, planName, feature }: { value: CellValue; planName: string; feature: string }) {
  if (typeof value === "boolean") {
    return (
      <td className="px-4 py-3.5 text-center">
        {value ? (
          <span className="inline-flex items-center justify-center" aria-label={`${planName}: ${feature} incluido`}>
            <Check className="h-5 w-5 text-primary-600 dark:text-primary-400" aria-hidden="true" />
          </span>
        ) : (
          <span className="inline-flex items-center justify-center" aria-label={`${planName}: ${feature} no incluido`}>
            <X className="h-5 w-5 text-slate-300 dark:text-zinc-600" aria-hidden="true" />
          </span>
        )}
      </td>
    );
  }

  return (
    <td className="px-4 py-3.5 text-center text-sm text-slate-700 dark:text-zinc-300">
      {value}
    </td>
  );
}

// ─── Mobile Stacked Cards ─────────────────────────────────────────────────────

function MobileComparisonCards() {
  const planKeys: Array<keyof Omit<FeatureRow, "feature">> = [
    "gratis",
    "starter",
    "pro",
    "clinica",
    "enterprise",
  ];

  return (
    <div className="lg:hidden space-y-6">
      {PLAN_HEADERS.map((planName, planIdx) => {
        const key = planKeys[planIdx];
        return (
          <div
            key={planName}
            className={cn(
              "rounded-xl border border-[hsl(var(--border))] overflow-hidden",
              planName === "Pro" && "border-primary-600 border-2",
            )}
          >
            {/* Plan header */}
            <div
              className={cn(
                "px-4 py-3 font-semibold text-sm",
                planName === "Pro"
                  ? "bg-primary-600 text-white"
                  : "bg-[hsl(var(--muted))] text-slate-700 dark:text-zinc-300",
              )}
            >
              {planName}
              {planName === "Pro" && (
                <span className="ml-2 text-xs font-normal opacity-80">
                  Mas popular
                </span>
              )}
            </div>

            {/* Feature rows */}
            {FEATURE_MATRIX.map((cat) => (
              <div key={cat.category}>
                <div className="px-4 py-2 text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-zinc-500 bg-slate-50 dark:bg-zinc-900/50">
                  {cat.category}
                </div>
                {cat.rows.map((row, rowIdx) => {
                  const val = row[key];
                  return (
                    <div
                      key={row.feature}
                      className={cn(
                        "flex items-center justify-between px-4 py-2.5 text-sm",
                        rowIdx % 2 === 0
                          ? "bg-white dark:bg-zinc-950"
                          : "bg-slate-50/50 dark:bg-zinc-900/30",
                      )}
                    >
                      <span className="text-slate-700 dark:text-zinc-300">
                        {row.feature}
                      </span>
                      {typeof val === "boolean" ? (
                        val ? (
                          <Check className="h-4 w-4 text-primary-600 dark:text-primary-400 shrink-0" aria-label="Incluido" />
                        ) : (
                          <X className="h-4 w-4 text-slate-300 dark:text-zinc-600 shrink-0" aria-label="No incluido" />
                        )
                      ) : (
                        <span className="text-slate-600 dark:text-zinc-400 text-xs">
                          {val}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}

// ─── Desktop Table ─────────────────────────────────────────────────────────────

function DesktopTable() {
  return (
    <div className="hidden lg:block overflow-x-auto rounded-xl border border-[hsl(var(--border))]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[hsl(var(--border))]">
            <th className="px-6 py-4 text-left font-semibold text-slate-700 dark:text-zinc-300 w-1/3 bg-[hsl(var(--muted))]">
              Funcion
            </th>
            {PLAN_HEADERS.map((plan) => (
              <th
                key={plan}
                className={cn(
                  "px-4 py-4 text-center font-semibold text-sm w-[13%]",
                  plan === "Pro"
                    ? "bg-primary-600 text-white"
                    : "bg-[hsl(var(--muted))] text-slate-700 dark:text-zinc-300",
                )}
              >
                {plan}
                {plan === "Pro" && (
                  <div className="text-xs font-normal opacity-80 mt-0.5">
                    Mas popular
                  </div>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {FEATURE_MATRIX.map((category) => (
            <>
              {/* Category header row */}
              <tr
                key={`cat-${category.category}`}
                className="border-t border-[hsl(var(--border))]"
              >
                <td
                  colSpan={6}
                  className="px-6 py-2 text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-zinc-500 bg-slate-50 dark:bg-zinc-900/50"
                >
                  {category.category}
                </td>
              </tr>

              {/* Feature rows */}
              {category.rows.map((row, rowIdx) => (
                <tr
                  key={row.feature}
                  className={cn(
                    "border-t border-[hsl(var(--border))]/50 transition-colors duration-100",
                    rowIdx % 2 === 0
                      ? "bg-white dark:bg-zinc-950"
                      : "bg-slate-50/50 dark:bg-zinc-900/20",
                    "hover:bg-slate-50 dark:hover:bg-zinc-900/40",
                  )}
                >
                  <td className="px-6 py-3.5 text-slate-700 dark:text-zinc-300 font-medium">
                    {row.feature}
                  </td>
                  <TableCell value={row.gratis} planName="Gratis" feature={row.feature} />
                  <TableCell value={row.starter} planName="Starter" feature={row.feature} />
                  <TableCell
                    value={row.pro}
                    planName="Pro"
                    feature={row.feature}
                  />
                  <TableCell value={row.clinica} planName="Clinica" feature={row.feature} />
                  <TableCell value={row.enterprise} planName="Enterprise" feature={row.feature} />
                </tr>
              ))}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Main Export ───────────────────────────────────────────────────────────────

export function PricingTable() {
  return (
    <section
      className="py-16 px-4 sm:px-6 lg:px-8 bg-slate-50/50 dark:bg-zinc-900/30"
      aria-labelledby="comparison-heading"
    >
      <div className="mx-auto max-w-7xl">
        <div className="text-center mb-10">
          <h2
            id="comparison-heading"
            className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-zinc-50"
          >
            Compara todos los planes
          </h2>
          <p className="mt-3 text-slate-600 dark:text-zinc-400">
            Elige el plan que mejor se adapta al tamano y necesidades de tu clinica.
          </p>
        </div>

        {/* Desktop table */}
        <DesktopTable />

        {/* Mobile stacked cards */}
        <MobileComparisonCards />
      </div>
    </section>
  );
}
