"""Compliance adapter registry and resolution (ADR-007).

Maps country codes to adapter implementations. Resolved at runtime
via FastAPI dependency injection from the tenant's country_code.
"""

from app.compliance.base import ComplianceAdapter
from app.core.exceptions import ComplianceError

_ADAPTER_REGISTRY: dict[str, type[ComplianceAdapter]] = {}


def register_adapter(adapter_class: type[ComplianceAdapter]) -> None:
    """Register a compliance adapter class for its country code.

    The adapter class must implement ComplianceAdapter and define
    a country_code property. The class is instantiated on registration
    to read the country_code, then stored by that key.
    """
    instance = adapter_class()
    _ADAPTER_REGISTRY[instance.country_code] = adapter_class


def get_compliance_adapter(country_code: str) -> ComplianceAdapter:
    """Look up and instantiate the compliance adapter for a country code.

    Raises ComplianceError if no adapter is registered for the given country.
    """
    adapter_class = _ADAPTER_REGISTRY.get(country_code)
    if adapter_class is None:
        raise ComplianceError(
            error="COMPLIANCE_unsupported_country",
            message=(
                f"No compliance adapter registered for country: {country_code}. "
                f"Supported countries: {list(_ADAPTER_REGISTRY.keys())}"
            ),
            status_code=404,
        )
    return adapter_class()


# Register available adapters at module load time.
# Colombia is MVP; Mexico stub added in Sprint 15-16.
from app.compliance.colombia.adapter import ColombiaComplianceAdapter  # noqa: E402
from app.compliance.mexico.adapter import MexicoComplianceAdapter  # noqa: E402

register_adapter(ColombiaComplianceAdapter)
register_adapter(MexicoComplianceAdapter)
