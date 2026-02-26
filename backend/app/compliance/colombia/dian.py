"""DIAN e-invoicing integration via MATIAS API (CO-06, CO-07, INT-10).

Handles:
  - CUFE computation (SHA-384 per DIAN formula)
  - UBL 2.1 XML generation for dental invoices
  - X.509 XML signing (placeholder -- requires real certificate)
  - MATIAS API client for submission and status checking

Dental services are IVA-exempt in Colombia (health services exclusion).
"""

import hashlib
import logging
from xml.etree.ElementTree import Element, SubElement, tostring

import httpx

from app.core.config import settings

logger = logging.getLogger("dentalos.compliance.dian")

# MATIAS API timeout (seconds)
_TIMEOUT = 30.0


class MATIASClient:
    """Async HTTP client for the MATIAS e-invoicing API.

    Uses HTTP Basic authentication with DentalOS-level credentials
    (Casa de Software model).  Per-clinic NIT and DIAN config come from
    TenantEInvoiceConfig.
    """

    def __init__(self) -> None:
        self.base_url = settings.matias_base_url
        self.client_id = settings.matias_client_id
        self.secret = settings.matias_secret

    def _auth(self) -> tuple[str, str]:
        """Return HTTP Basic auth tuple."""
        return (self.client_id, self.secret)

    async def submit_invoice(
        self,
        *,
        xml_content: str,
        nit: str,
        environment: str = "test",
    ) -> dict:
        """Submit a UBL 2.1 XML invoice to MATIAS.

        Returns MATIAS response with submission_id and initial status.
        """
        url = f"{self.base_url}/api/v1/invoices"

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                url,
                auth=self._auth(),
                json={
                    "xml": xml_content,
                    "nit_emisor": nit,
                    "ambiente": "1" if environment == "production" else "2",
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    async def check_status(self, submission_id: str) -> dict:
        """Check the status of a previously submitted invoice.

        Returns MATIAS response with DIAN acceptance status.
        """
        url = f"{self.base_url}/api/v1/invoices/{submission_id}/status"

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url, auth=self._auth())
            response.raise_for_status()
            return response.json()


def compute_cufe(
    *,
    invoice_number: str,
    issue_date: str,
    issue_time: str,
    subtotal: str,
    tax_code: str,
    tax_amount: str,
    total: str,
    nit_emisor: str,
    nit_receptor: str,
    technical_key: str,
    environment: str = "test",
) -> str:
    """Compute the CUFE (Codigo Unico de Facturacion Electronica).

    Per DIAN specification, the CUFE is a SHA-384 hash of:
      NumFac + FecFac + HorFac + ValFac + CodImp1 + ValImp1 + ValTot +
      NitOFE + NumAdq + ClTec + TipoAmbiente

    All values are concatenated without separators.
    Dental services are IVA-exempt, so tax fields are typically "01" and "0.00".
    """
    cufe_input = "".join([
        invoice_number,
        issue_date,
        issue_time,
        subtotal,
        tax_code,
        tax_amount,
        total,
        nit_emisor,
        nit_receptor,
        technical_key,
        "1" if environment == "production" else "2",
    ])
    return hashlib.sha384(cufe_input.encode("utf-8")).hexdigest()


def build_ubl_xml(
    *,
    invoice_number: str,
    issue_date: str,
    issue_time: str,
    cufe: str,
    nit_emisor: str,
    nit_dv_emisor: str,
    emisor_name: str,
    nit_receptor: str,
    receptor_name: str,
    receptor_doc_type: str,
    subtotal_cents: int,
    tax_cents: int,
    total_cents: int,
    line_items: list[dict],
    currency: str = "COP",
    environment: str = "test",
) -> str:
    """Build a UBL 2.1 XML document for DIAN submission.

    This is a simplified dental invoice XML.  Full production implementation
    would include additional namespaces, extensions, and DIAN-specific elements.

    Monetary values are converted from cents to decimal strings.
    """
    # UBL 2.1 namespaces
    ns = {
        "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": (
            "urn:oasis:names:specification:ubl:schema:xsd:"
            "CommonAggregateComponents-2"
        ),
        "cbc": (
            "urn:oasis:names:specification:ubl:schema:xsd:"
            "CommonBasicComponents-2"
        ),
    }

    root = Element("Invoice", xmlns=ns[""])
    root.set("xmlns:cac", ns["cac"])
    root.set("xmlns:cbc", ns["cbc"])

    # Header
    _add_text(root, "cbc:UBLVersionID", "UBL 2.1")
    _add_text(root, "cbc:ProfileID", "DIAN 2.1")
    _add_text(root, "cbc:ID", invoice_number)
    _add_text(root, "cbc:UUID", cufe)
    _add_text(root, "cbc:IssueDate", issue_date)
    _add_text(root, "cbc:IssueTime", issue_time)
    _add_text(root, "cbc:InvoiceTypeCode", "01")  # Standard invoice
    _add_text(root, "cbc:DocumentCurrencyCode", currency)

    # Supplier (emisor)
    supplier = SubElement(root, "cac:AccountingSupplierParty")
    supplier_party = SubElement(supplier, "cac:Party")
    supplier_id = SubElement(supplier_party, "cac:PartyIdentification")
    sid_el = _add_text(supplier_id, "cbc:ID", nit_emisor)
    sid_el.set("schemeID", nit_dv_emisor)
    sid_el.set("schemeName", "31")  # NIT
    supplier_name_el = SubElement(supplier_party, "cac:PartyName")
    _add_text(supplier_name_el, "cbc:Name", emisor_name)

    # Customer (receptor)
    customer = SubElement(root, "cac:AccountingCustomerParty")
    customer_party = SubElement(customer, "cac:Party")
    customer_id = SubElement(customer_party, "cac:PartyIdentification")
    cid_el = _add_text(customer_id, "cbc:ID", nit_receptor)
    cid_el.set("schemeName", _doc_type_to_dian_code(receptor_doc_type))
    customer_name_el = SubElement(customer_party, "cac:PartyName")
    _add_text(customer_name_el, "cbc:Name", receptor_name)

    # Tax total (IVA-exempt for dental services)
    tax_total = SubElement(root, "cac:TaxTotal")
    tax_amount_el = SubElement(tax_total, "cbc:TaxAmount")
    tax_amount_el.text = _cents_to_decimal(tax_cents)
    tax_amount_el.set("currencyID", currency)

    # Legal monetary total
    monetary_total = SubElement(root, "cac:LegalMonetaryTotal")
    line_ext = SubElement(monetary_total, "cbc:LineExtensionAmount")
    line_ext.text = _cents_to_decimal(subtotal_cents)
    line_ext.set("currencyID", currency)
    payable = SubElement(monetary_total, "cbc:PayableAmount")
    payable.text = _cents_to_decimal(total_cents)
    payable.set("currencyID", currency)

    # Invoice lines
    for idx, item in enumerate(line_items, start=1):
        line = SubElement(root, "cac:InvoiceLine")
        _add_text(line, "cbc:ID", str(idx))
        qty = SubElement(line, "cbc:InvoicedQuantity")
        qty.text = str(item.get("quantity", 1))
        qty.set("unitCode", "EA")
        line_total = SubElement(line, "cbc:LineExtensionAmount")
        line_total.text = _cents_to_decimal(item.get("line_total", 0))
        line_total.set("currencyID", currency)

        # Item description
        inv_item = SubElement(line, "cac:Item")
        _add_text(inv_item, "cbc:Description", item.get("description", ""))
        if item.get("cups_code"):
            item_std_id = SubElement(inv_item, "cac:StandardItemIdentification")
            _add_text(item_std_id, "cbc:ID", item["cups_code"])

    return tostring(root, encoding="unicode", xml_declaration=True)


def sign_xml(xml_content: str, certificate_path: str | None = None) -> str:
    """Sign UBL XML with X.509 certificate for DIAN.

    MVP stub: returns XML as-is.  Production implementation will use
    the lxml library with xmlsec to apply XAdES-EPES signature using
    the clinic's DIAN certificate from S3.
    """
    # TODO: Production -- download cert from S3, apply XAdES-EPES signature
    # using lxml + xmlsec.  Required for DIAN production environment.
    logger.warning("XML signing is a stub -- not signing for MVP.")
    return xml_content


# ---- Internal helpers --------------------------------------------------------


def _add_text(parent: Element, tag: str, text: str) -> Element:
    """Add a child element with text content."""
    el = SubElement(parent, tag)
    el.text = text
    return el


def _cents_to_decimal(cents: int) -> str:
    """Convert cents integer to decimal string (e.g. 150000 -> '1500.00')."""
    return f"{cents / 100:.2f}"


def _doc_type_to_dian_code(doc_type: str) -> str:
    """Map DentalOS document_type to DIAN scheme code.

    DIAN codes:
      13 = Cedula de ciudadania (CC)
      22 = Cedula de extranjeria (CE)
      41 = Pasaporte (PA)
      47 = PEP
      12 = Tarjeta de identidad (TI)
      31 = NIT
    """
    mapping = {
        "CC": "13",
        "CE": "22",
        "PA": "41",
        "PEP": "47",
        "TI": "12",
        "NIT": "31",
    }
    return mapping.get(doc_type, "13")
