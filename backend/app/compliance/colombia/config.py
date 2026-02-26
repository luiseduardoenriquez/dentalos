"""Static Colombia compliance configuration (CO-08).

Contains 41 RDA field definitions, document types, code systems,
retention rules, and regulatory references for Resolución 1888.
"""

# ─── RDA Field Definitions (41 fields per Resolución 1888) ─────────────────────

# Severity weights: critical=3, required=2, recommended=1
RDA_FIELDS: list[dict] = [
    # Module: patient_demographics (8 fields)
    {"field": "document_type", "module": "patient_demographics", "label": "Tipo de documento", "severity": "critical", "weight": 3},
    {"field": "document_number", "module": "patient_demographics", "label": "Número de documento", "severity": "critical", "weight": 3},
    {"field": "first_name", "module": "patient_demographics", "label": "Primer nombre", "severity": "critical", "weight": 3},
    {"field": "last_name", "module": "patient_demographics", "label": "Primer apellido", "severity": "critical", "weight": 3},
    {"field": "birth_date", "module": "patient_demographics", "label": "Fecha de nacimiento", "severity": "critical", "weight": 3},
    {"field": "gender", "module": "patient_demographics", "label": "Sexo", "severity": "critical", "weight": 3},
    {"field": "phone", "module": "patient_demographics", "label": "Teléfono", "severity": "required", "weight": 2},
    {"field": "address", "module": "patient_demographics", "label": "Dirección", "severity": "required", "weight": 2},
    # Module: odontogram (10 fields)
    {"field": "initial_odontogram", "module": "odontogram", "label": "Odontograma inicial", "severity": "critical", "weight": 3},
    {"field": "tooth_number_fdi", "module": "odontogram", "label": "Número dental FDI", "severity": "critical", "weight": 3},
    {"field": "condition_code", "module": "odontogram", "label": "Código de hallazgo", "severity": "critical", "weight": 3},
    {"field": "condition_description", "module": "odontogram", "label": "Descripción del hallazgo", "severity": "required", "weight": 2},
    {"field": "tooth_state", "module": "odontogram", "label": "Estado del diente", "severity": "critical", "weight": 3},
    {"field": "surface_detail", "module": "odontogram", "label": "Detalle de superficie", "severity": "required", "weight": 2},
    {"field": "odontogram_date", "module": "odontogram", "label": "Fecha del odontograma", "severity": "critical", "weight": 3},
    {"field": "practitioner_name", "module": "odontogram", "label": "Nombre del profesional", "severity": "required", "weight": 2},
    {"field": "practitioner_license", "module": "odontogram", "label": "Registro profesional", "severity": "critical", "weight": 3},
    {"field": "odontogram_signature", "module": "odontogram", "label": "Firma digital odontograma", "severity": "recommended", "weight": 1},
    # Module: clinical_records (12 fields)
    {"field": "chief_complaint", "module": "clinical_records", "label": "Motivo de consulta", "severity": "critical", "weight": 3},
    {"field": "current_illness", "module": "clinical_records", "label": "Enfermedad actual", "severity": "required", "weight": 2},
    {"field": "medical_history", "module": "clinical_records", "label": "Antecedentes médicos", "severity": "critical", "weight": 3},
    {"field": "family_history", "module": "clinical_records", "label": "Antecedentes familiares", "severity": "recommended", "weight": 1},
    {"field": "physical_exam", "module": "clinical_records", "label": "Examen físico", "severity": "required", "weight": 2},
    {"field": "diagnosis_cie10", "module": "clinical_records", "label": "Diagnóstico CIE-10", "severity": "critical", "weight": 3},
    {"field": "diagnosis_type", "module": "clinical_records", "label": "Tipo de diagnóstico", "severity": "required", "weight": 2},
    {"field": "evolution_note", "module": "clinical_records", "label": "Nota de evolución", "severity": "required", "weight": 2},
    {"field": "procedure_cups", "module": "clinical_records", "label": "Procedimiento CUPS", "severity": "critical", "weight": 3},
    {"field": "record_date", "module": "clinical_records", "label": "Fecha del registro", "severity": "critical", "weight": 3},
    {"field": "record_practitioner", "module": "clinical_records", "label": "Profesional tratante", "severity": "critical", "weight": 3},
    {"field": "record_signature", "module": "clinical_records", "label": "Firma digital registro", "severity": "recommended", "weight": 1},
    # Module: treatment_plans (7 fields)
    {"field": "tp_diagnosis", "module": "treatment_plans", "label": "Diagnóstico del plan", "severity": "critical", "weight": 3},
    {"field": "tp_procedures", "module": "treatment_plans", "label": "Procedimientos planificados", "severity": "critical", "weight": 3},
    {"field": "tp_prognosis", "module": "treatment_plans", "label": "Pronóstico", "severity": "required", "weight": 2},
    {"field": "tp_informed_consent", "module": "treatment_plans", "label": "Consentimiento informado", "severity": "critical", "weight": 3},
    {"field": "tp_cost_estimate", "module": "treatment_plans", "label": "Estimado de costos", "severity": "required", "weight": 2},
    {"field": "tp_practitioner", "module": "treatment_plans", "label": "Profesional responsable", "severity": "critical", "weight": 3},
    {"field": "tp_patient_acceptance", "module": "treatment_plans", "label": "Aceptación del paciente", "severity": "required", "weight": 2},
    # Module: consents (4 fields)
    {"field": "consent_template", "module": "consents", "label": "Plantilla de consentimiento", "severity": "critical", "weight": 3},
    {"field": "consent_patient_signature", "module": "consents", "label": "Firma del paciente", "severity": "critical", "weight": 3},
    {"field": "consent_witness", "module": "consents", "label": "Testigo/acompañante", "severity": "recommended", "weight": 1},
    {"field": "consent_date", "module": "consents", "label": "Fecha del consentimiento", "severity": "critical", "weight": 3},
]

# Module labels for display
RDA_MODULES: dict[str, str] = {
    "patient_demographics": "Datos del paciente",
    "odontogram": "Odontograma",
    "clinical_records": "Historia clínica",
    "treatment_plans": "Planes de tratamiento",
    "consents": "Consentimientos",
}

# ─── Document Types ─────────────────────────────────────────────────────────────

DOCUMENT_TYPES: list[dict] = [
    {"code": "CC", "label": "Cédula de ciudadanía"},
    {"code": "TI", "label": "Tarjeta de identidad"},
    {"code": "CE", "label": "Cédula de extranjería"},
    {"code": "PA", "label": "Pasaporte"},
    {"code": "RC", "label": "Registro civil"},
    {"code": "MS", "label": "Menor sin identificación"},
    {"code": "AS", "label": "Adulto sin identificación"},
    {"code": "NIT", "label": "NIT"},
    {"code": "CD", "label": "Carné diplomático"},
    {"code": "SC", "label": "Salvoconducto"},
    {"code": "PE", "label": "Permiso Especial de Permanencia"},
]

# ─── Code Systems ────────────────────────────────────────────────────────────────

CODE_SYSTEMS: dict = {
    "diagnosis": {
        "system": "CIE-10",
        "version": "2024",
        "description": "Clasificación Internacional de Enfermedades, 10ª revisión",
        "pattern": r"^[A-Z][0-9]{2}(\.[0-9]{1,4})?$",
    },
    "procedures": {
        "system": "CUPS",
        "version": "2024",
        "description": "Clasificación Única de Procedimientos en Salud",
        "pattern": r"^[0-9]{6}$",
    },
    "medications": {
        "system": "CUMS",
        "version": "2024",
        "description": "Código Único de Medicamentos Sanitarios",
        "pattern": r"^[0-9]{5,8}$",
    },
}

# ─── Retention Rules ─────────────────────────────────────────────────────────────

RETENTION_RULES: dict = {
    "clinical_records": {"years": 10, "regulation": "Resolución 1995 de 1999"},
    "images": {"years": 5, "regulation": "Resolución 1995 de 1999"},
    "invoices": {"years": 10, "regulation": "Estatuto Tributario Art. 632"},
    "consents": {"years": 10, "regulation": "Resolución 1995 de 1999"},
    "prescriptions": {"years": 5, "regulation": "Decreto 2200 de 2005"},
    "rips_files": {"years": 5, "regulation": "Resolución 3374 de 2000"},
}

# ─── Regulatory References ─────────────────────────────────────────────────────

REGULATORY_REFERENCES: list[dict] = [
    {"code": "R1888", "title": "Resolución 1888 de 2025", "topic": "RDA — Registro Dental Automatizado", "deadline": "2026-04-01"},
    {"code": "R1995", "title": "Resolución 1995 de 1999", "topic": "Manejo de historia clínica", "deadline": None},
    {"code": "R3374", "title": "Resolución 3374 de 2000", "topic": "RIPS — Registro Individual de Prestación de Servicios", "deadline": None},
    {"code": "L527", "title": "Ley 527 de 1999", "topic": "Firmas digitales y documentos electrónicos", "deadline": None},
    {"code": "R2003", "title": "Resolución 2003 de 2014", "topic": "Habilitación de servicios de salud", "deadline": None},
    {"code": "ET632", "title": "Estatuto Tributario Art. 632", "topic": "Conservación de documentos contables", "deadline": None},
]

# ─── Feature Flags ─────────────────────────────────────────────────────────────

FEATURE_FLAGS: dict = {
    "rda_enabled": True,
    "rips_enabled": True,
    "einvoice_enabled": True,
    "einvoice_sandbox": True,
    "rda_deadline": "2026-04-01",
}

# ─── Locale ────────────────────────────────────────────────────────────────────

LOCALE: dict = {
    "language": "es-419",
    "currency": "COP",
    "timezone": "America/Bogota",
    "date_format": "DD/MM/YYYY",
}
