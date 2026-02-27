import { ChevronDown } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface FaqItem {
  id: string;
  question: string;
  answer: string;
}

// ─── FAQ Data ─────────────────────────────────────────────────────────────────

const FAQS: FaqItem[] = [
  {
    id: "plan-gratuito",
    question: "Que incluye el plan gratuito?",
    answer:
      "El plan Gratis incluye 1 doctor, hasta 50 pacientes activos, odontograma digital basico y agenda de citas. Es ideal para consultorios que estan comenzando o quieren conocer la plataforma sin ningun compromiso. No se requiere tarjeta de credito para empezar.",
  },
  {
    id: "seguridad-datos",
    question: "Mis datos estan seguros?",
    answer:
      "Si. Todos los datos clinicos estan encriptados en reposo y en transito con TLS 1.3. Los servidores estan alojados en centros de datos certificados con backups diarios automaticos. Cumplimos con la Ley 1581 de Habeas Data de Colombia y las normas de proteccion de informacion de salud. Nunca vendemos ni compartimos datos de pacientes.",
  },
  {
    id: "resolucion-1888",
    question: "Cumple con la Resolucion 1888 y la generacion de RIPS?",
    answer:
      "Si, desde el plan Pro. DentalOS genera automaticamente el archivo RIPS en el formato requerido por el Ministerio de Salud de Colombia. Tambien cumple con los requerimientos de la Resolucion 1888 para la historia clinica electronica, incluyendo firma digital legal segun la Ley 527/1999.",
  },
  {
    id: "migracion-datos",
    question: "Puedo migrar mis datos desde otro software?",
    answer:
      "Si. Ofrecemos importacion de pacientes y datos basicos via archivo CSV para todos los planes de pago. Los planes Clinica y Enterprise incluyen migracion asistida por nuestro equipo, donde nos encargamos de trasladar historias clinicas, radiografias y datos de facturacion desde tu software actual sin interrumpir tu operacion.",
  },
  {
    id: "varias-sedes",
    question: "Funciona para clinicas con varias sedes?",
    answer:
      "Si. El plan Clinica esta disenado especificamente para redes de consultorios con multiples sedes. Tendras un unico dashboard para gestionar todas tus sedes, con roles y permisos granulares por sede, reportes consolidados y facturacion unificada. El plan Enterprise soporta redes de gran escala con configuraciones personalizadas.",
  },
  {
    id: "cancelar",
    question: "Puedo cancelar en cualquier momento?",
    answer:
      "Si, sin permanencia minima. Puedes cancelar tu suscripcion en cualquier momento desde tu panel de administracion. Al cancelar, tu cuenta pasa a modo lectura por 30 dias para que puedas exportar tus datos. Siempre podras descargar toda tu informacion en formatos estandar (CSV, PDF, JSON). Tus datos son tuyos.",
  },
  {
    id: "metodos-pago",
    question: "Que metodos de pago aceptan?",
    answer:
      "Aceptamos tarjeta de credito y debito (Visa, Mastercard, Amex), PSE para bancos colombianos, y transferencia bancaria para planes anuales o Enterprise. Tambien ofrecemos facturacion en COP para clinicas que lo requieran. Contacta a nuestro equipo de ventas para conocer todas las opciones.",
  },
];

// ─── FAQ Item Component ────────────────────────────────────────────────────────

function FaqItem({ item }: { item: FaqItem }) {
  return (
    <details
      className="group border-b border-[hsl(var(--border))] last:border-b-0"
      name="faq-accordion"
    >
      <summary
        className={[
          "flex items-center justify-between gap-4 py-5 px-1 cursor-pointer",
          "list-none select-none",
          "text-base font-medium text-slate-900 dark:text-zinc-100",
          "hover:text-primary-600 dark:hover:text-primary-400",
          "transition-colors duration-150",
          // Remove default disclosure triangle on all browsers
          "[&::-webkit-details-marker]:hidden",
        ].join(" ")}
      >
        <span>{item.question}</span>
        <ChevronDown
          className={[
            "h-5 w-5 shrink-0 text-slate-400 dark:text-zinc-500",
            "transition-transform duration-300 ease-in-out",
            "group-open:rotate-180 group-open:text-primary-600 dark:group-open:text-primary-400",
          ].join(" ")}
          aria-hidden="true"
        />
      </summary>

      <div className="px-1 pb-5">
        <p className="text-sm leading-relaxed text-slate-600 dark:text-zinc-400">
          {item.answer}
        </p>
      </div>
    </details>
  );
}

// ─── Main Export ───────────────────────────────────────────────────────────────

export function FaqSection() {
  return (
    <section
      className="py-16 px-4 sm:px-6 lg:px-8 bg-slate-50/50 dark:bg-zinc-900/30"
      aria-labelledby="faq-heading"
    >
      <div className="mx-auto max-w-3xl">
        {/* Section header */}
        <div className="text-center mb-10">
          <h2
            id="faq-heading"
            className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-zinc-50"
          >
            Preguntas frecuentes
          </h2>
          <p className="mt-3 text-slate-600 dark:text-zinc-400">
            Todo lo que necesitas saber antes de empezar. Si no encuentras tu
            pregunta,{" "}
            <a
              href="mailto:hola@dentalos.co"
              className="text-primary-600 dark:text-primary-400 hover:underline underline-offset-4"
            >
              escríbenos
            </a>
            .
          </p>
        </div>

        {/* FAQ accordion */}
        <div
          className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-950 divide-y divide-[hsl(var(--border))] px-6"
          role="list"
          aria-label="Preguntas frecuentes"
        >
          {FAQS.map((faq) => (
            <div key={faq.id} role="listitem">
              <FaqItem item={faq} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
