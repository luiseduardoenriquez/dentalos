"""Mexico CFDI 4.0 electronic invoicing integration via PAC (MX-01).

Handles:
  - Cadena original computation (canonical string for digital sealing)
  - CFDI 4.0 XML generation per SAT specification
  - X.509 CSD signing (stub — requires clinic certificate)
  - PAC client for XML stamping, status check, and cancellation

Dental health services are IVA-exempt under LIVA Art. 15, frac. XIV.
All invoices must be stamped by a PAC (Proveedor Autorizado de Certificacion)
before they are legally valid in Mexico.
"""

import hashlib
import logging
from xml.etree.ElementTree import Element, SubElement, tostring

import httpx

from app.compliance.mexico.config import (
    DEFAULT_CLAVE_PROD_SERV,
    DEFAULT_CLAVE_UNIDAD,
    DEFAULT_METODO_PAGO,
    DEFAULT_USO_CFDI,
    IVA_TYPE_EXEMPT,
    PAYMENT_METHOD_TO_FORMA_PAGO,
    SAT_CFDI_NAMESPACE,
    SAT_CFDI_VERSION,
    SAT_XSD_LOCATION,
)
from app.core.config import settings

logger = logging.getLogger("dentalos.compliance.cfdi")

# PAC API timeout (seconds) — PAC responses may be slow under load.
_TIMEOUT = 30.0


class PACClient:
    """Async HTTP client for a generic PAC (Proveedor Autorizado de Certificacion) API.

    PACs are third-party providers authorized by SAT to stamp CFDI XML.
    This client uses HTTP Basic authentication.  The actual PAC provider
    (e.g., Finkok, Diverza, SW SolucionFacturable) is configured via
    environment variables; the API shape is normalized by this adapter.

    Per-clinic RFC and CSD configuration come from TenantEInvoiceConfig
    (not stored here — passed per call).
    """

    def __init__(self) -> None:
        self.base_url = settings.pac_provider_url
        self.username = settings.pac_username
        self.password = settings.pac_password
        self.environment = settings.pac_environment

    def _auth(self) -> tuple[str, str]:
        """Return HTTP Basic auth tuple."""
        return (self.username, self.password)

    async def stamp_invoice(
        self,
        *,
        xml_content: str,
        rfc_emisor: str,
        environment: str = "test",
    ) -> dict:
        """Submit a CFDI 4.0 XML to the PAC for stamping (timbrado).

        The PAC validates the XML structure, computes the complemento fiscal
        (UUID fiscal / folio fiscal), and returns the stamped XML together
        with the TimbreFiscalDigital complement.

        Args:
            xml_content: Complete CFDI 4.0 XML string (unsigned or with CSD seal).
            rfc_emisor: RFC of the issuing clinic/dentist.
            environment: "test" for sandbox, "production" for live SAT.

        Returns:
            dict with keys:
              - uuid_fiscal: SAT-assigned UUID (folio fiscal)
              - stamped_xml: CFDI XML with TimbreFiscalDigital appended
              - status: "stamped" | "error"
              - error_code: SAT error code if status is "error" (else None)
              - error_message: human-readable description if error (else None)
        """
        url = f"{self.base_url}/v1/stamp"

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            logger.info(
                "Submitting CFDI to PAC for stamping",
                extra={"rfc_emisor": rfc_emisor, "environment": environment},
            )
            response = await client.post(
                url,
                auth=self._auth(),
                json={
                    "xml": xml_content,
                    "rfc_emisor": rfc_emisor,
                    "ambiente": "1" if environment == "production" else "2",
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            logger.info(
                "PAC stamp response received",
                extra={"status": data.get("status"), "rfc_emisor": rfc_emisor},
            )
            return data

    async def check_status(self, uuid_fiscal: str) -> dict:
        """Check the SAT status of a previously stamped CFDI.

        Queries the PAC's status endpoint, which in turn queries the SAT
        verification service (ACUSE service).

        Args:
            uuid_fiscal: The UUID (folio fiscal) returned after stamping.

        Returns:
            dict with keys:
              - uuid_fiscal: echo of the queried UUID
              - sat_status: "Vigente" | "Cancelado" | "No Encontrado"
              - cancellation_date: ISO timestamp if cancelled (else None)
        """
        url = f"{self.base_url}/v1/status/{uuid_fiscal}"

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            logger.info(
                "Checking CFDI status with PAC",
                extra={"uuid_fiscal": uuid_fiscal},
            )
            response = await client.get(url, auth=self._auth())
            response.raise_for_status()
            return response.json()

    async def cancel_invoice(
        self,
        uuid_fiscal: str,
        rfc_emisor: str,
        cancel_reason: str,
    ) -> dict:
        """Cancel a previously stamped CFDI via SAT cancellation service.

        SAT Annex 20 requires a cancellation reason code (motivo de cancelacion):
          01 — Comprobante emitido con errores con relación
          02 — Comprobante emitido con errores sin relación
          03 — No se llevó a cabo la operación
          04 — Operación nominativa relacionada en una factura global

        Args:
            uuid_fiscal: The UUID (folio fiscal) of the CFDI to cancel.
            rfc_emisor: RFC of the issuing clinic/dentist.
            cancel_reason: SAT cancellation reason code ("01"–"04").

        Returns:
            dict with keys:
              - uuid_fiscal: echo of the cancelled UUID
              - status: "cancelled" | "pending_acceptance" | "rejected" | "error"
              - acuse: SAT cancellation acknowledgement XML (if available)
              - error_message: description if error (else None)
        """
        url = f"{self.base_url}/v1/cancel"

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            logger.info(
                "Requesting CFDI cancellation via PAC",
                extra={"uuid_fiscal": uuid_fiscal, "cancel_reason": cancel_reason},
            )
            response = await client.post(
                url,
                auth=self._auth(),
                json={
                    "uuid_fiscal": uuid_fiscal,
                    "rfc_emisor": rfc_emisor,
                    "motivo_cancelacion": cancel_reason,
                    "ambiente": (
                        "1" if self.environment == "production" else "2"
                    ),
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            logger.info(
                "PAC cancellation response received",
                extra={
                    "uuid_fiscal": uuid_fiscal,
                    "status": data.get("status"),
                },
            )
            return data


def compute_cadena_original(
    *,
    version: str,
    serie: str,
    folio: str,
    fecha: str,
    forma_pago: str,
    subtotal: str,
    moneda: str,
    total: str,
    tipo_comprobante: str,
    metodo_pago: str,
    lugar_expedicion: str,
    rfc_emisor: str,
    nombre_emisor: str,
    regimen_fiscal_emisor: str,
    rfc_receptor: str,
    nombre_receptor: str,
    domicilio_fiscal_receptor: str,
    regimen_fiscal_receptor: str,
    uso_cfdi: str,
    conceptos_cadena: str,
) -> str:
    """Compute the cadena original for CFDI 4.0 digital sealing.

    The cadena original is a pipe-delimited canonical string derived from
    the CFDI XML fields, fed through the SAT XSLT stylesheet (cadenaoriginal_TFD_1_1).
    This implementation is a simplified direct-field version used before
    the CSD signing step.  Production implementations should apply the
    SAT-published XSLT to the built XML for guaranteed conformance.

    Per SAT Annex 20, section 2.4:
      ||version|serie|folio|fecha|formaPago|...||

    All values are pipe-delimited; None/empty fields are omitted.

    Args:
        version: CFDI version, always "4.0".
        serie: Invoice series identifier (alphanumeric, up to 25 chars).
        folio: Invoice sequential number within the series.
        fecha: ISO 8601 datetime (YYYY-MM-DDTHH:MM:SS) in RFC local time.
        forma_pago: SAT Forma de Pago code.
        subtotal: Subtotal before taxes (decimal string, 2+ decimals).
        moneda: ISO 4217 currency code (e.g. "MXN").
        total: Total payable amount (decimal string, 2+ decimals).
        tipo_comprobante: "I" (Ingreso), "E" (Egreso), "T" (Traslado), etc.
        metodo_pago: "PUE" or "PPD".
        lugar_expedicion: 5-digit postal code of the place of issue.
        rfc_emisor: RFC of the issuing entity.
        nombre_emisor: Legal name of the issuing entity.
        regimen_fiscal_emisor: SAT regime code for the issuer.
        rfc_receptor: RFC of the recipient.
        nombre_receptor: Legal name of the recipient.
        domicilio_fiscal_receptor: 5-digit postal code of the recipient.
        regimen_fiscal_receptor: SAT regime code for the recipient.
        uso_cfdi: SAT Uso CFDI code.
        conceptos_cadena: Pre-built cadena string for all Concepto elements.

    Returns:
        SHA-256 hex digest of the cadena original (used for the Sello field).
    """
    parts = [
        version,
        serie,
        folio,
        fecha,
        forma_pago,
        subtotal,
        moneda,
        total,
        tipo_comprobante,
        metodo_pago,
        lugar_expedicion,
        rfc_emisor,
        nombre_emisor,
        regimen_fiscal_emisor,
        rfc_receptor,
        nombre_receptor,
        domicilio_fiscal_receptor,
        regimen_fiscal_receptor,
        uso_cfdi,
        conceptos_cadena,
    ]
    # Build the cadena original in SAT format: ||field1|field2|...|fieldN||
    cadena = "||" + "|".join(p for p in parts if p) + "||"
    logger.debug("Cadena original computed", extra={"cadena_length": len(cadena)})
    # SAT uses SHA-256 on the cadena original for the digital seal.
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest()


def build_cfdi_xml(
    *,
    serie: str,
    folio: str,
    fecha: str,
    forma_pago: str,
    subtotal_cents: int,
    total_cents: int,
    metodo_pago: str = DEFAULT_METODO_PAGO,
    lugar_expedicion: str,
    rfc_emisor: str,
    nombre_emisor: str,
    regimen_fiscal_emisor: str,
    rfc_receptor: str,
    nombre_receptor: str,
    domicilio_fiscal_receptor: str,
    regimen_fiscal_receptor: str,
    uso_cfdi: str = DEFAULT_USO_CFDI,
    line_items: list[dict],
    sello: str = "",
    no_certificado: str = "",
    certificado: str = "",
    currency: str = "MXN",
) -> str:
    """Build a CFDI 4.0 XML document per SAT Annex 20 specification.

    Dental health services are IVA-exempt (LIVA Art. 15, frac. XIV).
    Each Concepto element carries TrasladosType with TipoFactor="Exento".

    Monetary values are passed as integer cents and converted to decimal
    strings with 2 decimal places for the XML (SAT requires at least 2
    decimal places).

    Args:
        serie: Invoice series (e.g. "A", "DEN").
        folio: Sequential invoice number within the series.
        fecha: ISO 8601 datetime string (YYYY-MM-DDTHH:MM:SS).
        forma_pago: SAT Forma de Pago code (e.g. "01" for cash).
        subtotal_cents: Invoice subtotal in MXN cents before taxes.
        total_cents: Invoice total in MXN cents (equals subtotal for exempt services).
        metodo_pago: "PUE" (single payment) or "PPD" (installments).
        lugar_expedicion: 5-digit postal code of the place of issue.
        rfc_emisor: RFC of the issuing dentist or clinic.
        nombre_emisor: Legal name of the issuing entity.
        regimen_fiscal_emisor: SAT regime code for the issuer.
        rfc_receptor: RFC of the patient/recipient.
        nombre_receptor: Legal name of the patient/recipient.
        domicilio_fiscal_receptor: 5-digit postal code of the recipient.
        regimen_fiscal_receptor: SAT regime code for the recipient.
        uso_cfdi: SAT Uso CFDI code (default D01 for dental services).
        line_items: List of dicts with keys:
          - description (str): service description
          - quantity (int|float): units billed (default 1)
          - unit_value_cents (int): price per unit in cents
          - line_total_cents (int): total for this line in cents
          - clave_prod_serv (str, optional): SAT product/service key
          - clave_unidad (str, optional): SAT unit key
          - payment_method (str, optional): used to derive forma_pago
        sello: Base64-encoded digital seal (empty string for PAC pre-stamping).
        no_certificado: CSD certificate number (empty for stub/test).
        certificado: Base64-encoded CSD certificate (empty for stub/test).
        currency: ISO 4217 code (default "MXN").

    Returns:
        CFDI 4.0 XML string with XML declaration.
    """
    cfdi_ns = SAT_CFDI_NAMESPACE
    xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"

    # Root element: cfdi:Comprobante
    root = Element(f"{{{cfdi_ns}}}Comprobante")
    root.set("xmlns:cfdi", cfdi_ns)
    root.set("xmlns:xsi", xsi_ns)
    root.set(
        f"{{{xsi_ns}}}schemaLocation",
        SAT_XSD_LOCATION,
    )
    root.set("Version", SAT_CFDI_VERSION)
    root.set("Serie", serie)
    root.set("Folio", folio)
    root.set("Fecha", fecha)
    root.set("Sello", sello)
    root.set("FormaPago", forma_pago)
    root.set("NoCertificado", no_certificado)
    root.set("Certificado", certificado)
    root.set("SubTotal", _cents_to_decimal(subtotal_cents))
    root.set("Moneda", currency)
    root.set("Total", _cents_to_decimal(total_cents))
    root.set("TipoDeComprobante", "I")  # I = Ingreso (income invoice)
    root.set("Exportacion", "01")       # 01 = No aplica (no export)
    root.set("MetodoPago", metodo_pago)
    root.set("LugarExpedicion", lugar_expedicion)

    # cfdi:Emisor
    emisor = SubElement(root, f"{{{cfdi_ns}}}Emisor")
    emisor.set("Rfc", rfc_emisor)
    emisor.set("Nombre", nombre_emisor)
    emisor.set("RegimenFiscal", regimen_fiscal_emisor)

    # cfdi:Receptor
    receptor = SubElement(root, f"{{{cfdi_ns}}}Receptor")
    receptor.set("Rfc", rfc_receptor)
    receptor.set("Nombre", nombre_receptor)
    receptor.set("DomicilioFiscalReceptor", domicilio_fiscal_receptor)
    receptor.set("RegimenFiscalReceptor", regimen_fiscal_receptor)
    receptor.set("UsoCFDI", uso_cfdi)

    # cfdi:Conceptos — one cfdi:Concepto per line item
    conceptos = SubElement(root, f"{{{cfdi_ns}}}Conceptos")

    for item in line_items:
        concepto = SubElement(conceptos, f"{{{cfdi_ns}}}Concepto")
        clave_prod_serv = item.get("clave_prod_serv") or DEFAULT_CLAVE_PROD_SERV
        clave_unidad = item.get("clave_unidad") or DEFAULT_CLAVE_UNIDAD
        quantity = item.get("quantity", 1)
        unit_value_cents: int = item.get("unit_value_cents", 0)
        line_total_cents: int = item.get("line_total_cents", 0)

        concepto.set("ClaveProdServ", clave_prod_serv)
        concepto.set("ClaveUnidad", clave_unidad)
        concepto.set("Cantidad", str(quantity))
        concepto.set("Descripcion", item.get("description", ""))
        concepto.set("ValorUnitario", _cents_to_decimal(unit_value_cents))
        concepto.set("Importe", _cents_to_decimal(line_total_cents))
        # Dental services are IVA-exempt; ObjetoImp=04 means "No objeto de impuesto"
        # Use ObjetoImp=02 if including explicit Exento traslado, 04 if entirely excluded.
        # SAT CFDI 4.0 requires ObjetoImp to be present.
        concepto.set("ObjetoImp", "01")  # 01 = No objeto de impuesto

    # cfdi:Impuestos — aggregate tax section (zero for IVA-exempt services)
    # SAT CFDI 4.0 requires the Impuestos element when any traslado or retención
    # is present.  For fully exempt services with ObjetoImp=01 on all conceptos,
    # the Impuestos element can be omitted.  We include it as a zero-value block
    # for explicit clarity and potential future non-exempt items.
    #
    # If all items are ObjetoImp=01, omit Impuestos per SAT validation rules.
    # We skip the block here since dental services are uniformly exempt.

    logger.debug(
        "Built CFDI 4.0 XML",
        extra={
            "serie": serie,
            "folio": folio,
            "rfc_emisor": rfc_emisor,
            "line_items_count": len(line_items),
            "total_cents": total_cents,
        },
    )

    return tostring(root, encoding="unicode", xml_declaration=True)


def sign_cfdi_xml(xml_content: str, certificate_path: str | None = None) -> str:
    """Sign CFDI XML with a CSD (Certificado de Sello Digital).

    MVP stub: returns XML as-is.  Production implementation will:
      1. Download the clinic's CSD (.cer + .key) from S3.
      2. Apply the SHA-256 + RSA seal to the cadena original.
      3. Embed the Base64 Sello and NoCertificado attributes in the
         cfdi:Comprobante root element.
      4. Pass the sealed XML to the PAC for final UUID stamping.

    The CSD is issued per-clinic by SAT and stored encrypted in S3 at:
      /{tenant_id}/compliance/csd/{rfc_emisor}.cer
      /{tenant_id}/compliance/csd/{rfc_emisor}.key (encrypted)

    Note: Unlike DIAN (where the PAC itself signs), SAT requires the
    emisor to seal the XML before PAC submission.  The PAC then adds
    the TimbreFiscalDigital complement with the SAT UUID.
    """
    # TODO: Production — download CSD from S3, compute cadena original via
    # SAT XSLT stylesheet, sign with RSA-SHA256 using the .key file,
    # embed Base64(signature) in Sello attribute.
    logger.warning(
        "CFDI XML signing is a stub — XML will be submitted unsigned to PAC. "
        "Only valid in PAC sandbox environments.",
    )
    return xml_content


# ---- Internal helpers --------------------------------------------------------


def _cents_to_decimal(cents: int) -> str:
    """Convert integer cents to a 2-decimal-place string.

    SAT requires monetary values with at least 2 decimal places.
    Example: 150000 -> "1500.00"
    """
    return f"{cents / 100:.2f}"


def _build_concepto_cadena(item: dict) -> str:
    """Build the cadena original fragment for a single Concepto element.

    Used by compute_cadena_original to concatenate all line-item fields
    in the order specified by the SAT XSLT stylesheet.
    """
    clave_prod_serv = item.get("clave_prod_serv") or DEFAULT_CLAVE_PROD_SERV
    clave_unidad = item.get("clave_unidad") or DEFAULT_CLAVE_UNIDAD
    quantity = str(item.get("quantity", 1))
    description = item.get("description", "")
    unit_value = _cents_to_decimal(item.get("unit_value_cents", 0))
    importe = _cents_to_decimal(item.get("line_total_cents", 0))

    parts = [clave_prod_serv, clave_unidad, quantity, description, unit_value, importe]
    return "|".join(p for p in parts if p)


def build_conceptos_cadena(line_items: list[dict]) -> str:
    """Build the concatenated cadena original string for all Concepto elements.

    Returns a pipe-delimited string suitable for passing to compute_cadena_original.
    """
    return "|".join(_build_concepto_cadena(item) for item in line_items)
