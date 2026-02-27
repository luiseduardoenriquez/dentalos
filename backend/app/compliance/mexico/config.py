"""Mexico SAT / CFDI 4.0 catalog constants.

These are the official SAT catalog values required for CFDI 4.0 XML construction.
All mappings are keyed by the code DentalOS stores internally.

References:
  - Catalogo de Uso CFDI: cat:c_UsoCFDI
  - Catalogo Regimen Fiscal: cat:c_RegimenFiscal
  - Catalogo Forma de Pago: cat:c_FormaPago
  - Catalogo Metodo de Pago: cat:c_MetodoPago
  - Catalogo Clave Unidad: cat:c_ClaveUnidad
"""

# -- Uso CFDI (cat:c_UsoCFDI) -------------------------------------------------
# Dental practice common codes.  D01 is the primary code for healthcare services.
USO_CFDI: dict[str, str] = {
    "D01": "Honorarios médicos, dentales y gastos hospitalarios",
    "D02": "Gastos médicos por incapacidad o discapacidad",
    "D07": "Primas por seguros de gastos médicos",
    "G01": "Adquisición de mercancias",
    "G03": "Gastos en general",
    "I01": "Construcciones",
    "S01": "Sin efectos fiscales",
}

# Default Uso CFDI for dental services billed to patients (individuals).
DEFAULT_USO_CFDI = "D01"

# Uso CFDI for services billed to legal entities (empresas) without a specific purpose.
EMPRESA_USO_CFDI = "G03"

# -- Regimen Fiscal (cat:c_RegimenFiscal) -------------------------------------
# Most dentists are physical persons (personas físicas) in regime 612.
# Clinics organized as legal entities use regime 601 or 603.
REGIMEN_FISCAL: dict[str, str] = {
    "601": "General de Ley Personas Morales",
    "603": "Personas Morales con Fines no Lucrativos",
    "605": "Sueldos y Salarios e Ingresos Asimilados a Salarios",
    "606": "Arrendamiento",
    "608": "Demás ingresos",
    "610": "Residentes en el Extranjero sin Establecimiento Permanente en México",
    "611": "Ingresos por Dividendos (socios y accionistas)",
    "612": "Personas Físicas con Actividades Empresariales y Profesionales",
    "614": "Ingresos por intereses",
    "616": "Sin obligaciones fiscales",
    "620": "Sociedades Cooperativas de Producción que optan por diferir sus ingresos",
    "621": "Incorporación Fiscal",
    "622": "Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras",
    "623": "Opcional para Grupos de Sociedades",
    "624": "Coordinados",
    "625": "Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas",
    "626": "Régimen Simplificado de Confianza",
}

# Default regime for dentists operating as physical persons (most common case).
DEFAULT_REGIMEN_FISCAL_PERSONA_FISICA = "612"

# Default regime for dental clinics organized as legal entities.
DEFAULT_REGIMEN_FISCAL_PERSONA_MORAL = "601"

# -- Forma de Pago (cat:c_FormaPago) ------------------------------------------
# Payment method at the time of invoice.
FORMA_PAGO: dict[str, str] = {
    "01": "Efectivo",
    "02": "Cheque nominativo",
    "03": "Transferencia electrónica de fondos",
    "04": "Tarjeta de crédito",
    "05": "Monedero electrónico",
    "06": "Dinero electrónico",
    "08": "Vales de despensa",
    "12": "Dación en pago",
    "13": "Pago por subrogación",
    "14": "Pago por consignación",
    "15": "Condonación",
    "17": "Compensación",
    "23": "Novación",
    "24": "Confusión",
    "25": "Remisión de deuda",
    "26": "Prescripción o caducidad",
    "27": "A satisfacción del acreedor",
    "28": "Tarjeta de débito",
    "29": "Tarjeta de servicios",
    "30": "Aplicación de anticipos",
    "31": "Intermediario pagos",
    "99": "Por definir",
}

# DentalOS payment_method → SAT Forma de Pago code mapping.
# Internal payment_method strings map to the SAT catalog codes above.
PAYMENT_METHOD_TO_FORMA_PAGO: dict[str, str] = {
    "cash": "01",
    "check": "02",
    "transfer": "03",
    "credit_card": "04",
    "debit_card": "28",
    "electronic_wallet": "05",
    "pending": "99",
}

# -- Metodo de Pago (cat:c_MetodoPago) ----------------------------------------
# Whether full payment is made at the time of invoice or in installments.
METODO_PAGO: dict[str, str] = {
    "PUE": "Pago en una sola exhibición",
    "PPD": "Pago en parcialidades o diferido",
}

# Default for dental services: single full payment.
DEFAULT_METODO_PAGO = "PUE"

# -- Clave Producto o Servicio (cat:c_ClaveProdServ) --------------------------
# SAT product/service key codes for common dental services.
# Full catalog has ~52,000 entries; these are the most relevant dental codes.
CLAVE_PROD_SERV_DENTAL: dict[str, str] = {
    "85121500": "Servicios de odontología general",
    "85121501": "Servicios de ortodoncia",
    "85121502": "Servicios de endodoncia",
    "85121503": "Servicios de periodoncia",
    "85121504": "Servicios de cirugía oral",
    "85121505": "Servicios de odontopediatría",
    "85121600": "Servicios de laboratorio dental",
    "85121700": "Radiología dental",
}

# Default key for general dental services when a specific code is not mapped.
DEFAULT_CLAVE_PROD_SERV = "85121500"

# -- Clave Unidad (cat:c_ClaveUnidad) -----------------------------------------
# Unit of measure codes.  Dental services are billed per service (act).
CLAVE_UNIDAD: dict[str, str] = {
    "ACT": "Actividad",
    "E48": "Unidad de servicio",
    "H87": "Pieza",
}

# Default unit for professional services.
DEFAULT_CLAVE_UNIDAD = "ACT"

# -- IVA / Tax configuration --------------------------------------------------
# Dental health services are IVA-exempt under Mexican tax law (LIVA Art. 15, frac. XIV).
# No IVA is charged; these constants are kept for completeness and potential
# future use if non-exempt items appear on the same invoice.
IVA_RATE_STANDARD = "0.160000"   # 16% standard rate (as decimal string per SAT format)
IVA_RATE_EXEMPT = "0.000000"     # Exento de IVA for health services
IVA_TYPE_EXEMPT = "Exento"       # SAT TipoFactor value for exempt items

# -- SAT environment endpoints -------------------------------------------------
SAT_CFDI_VERSION = "4.0"
SAT_CFDI_NAMESPACE = "http://www.sat.gob.mx/cfd/4"
SAT_XSD_LOCATION = (
    "http://www.sat.gob.mx/cfd/4 "
    "http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd"
)
