"""Random data helpers for load test scenarios.

Provides random patient IDs, doctor IDs, and test data generators
scoped to a virtual user's tenant.
"""

import random
import uuid
from datetime import date, timedelta

from load_tests.config import SEARCH_PREFIXES

# FDI tooth numbering: quadrant (1-4) + tooth (1-8)
FDI_TEETH = [f"{q}{t}" for q in range(1, 5) for t in range(1, 9)]

ZONES = ["mesial", "distal", "oclusal", "vestibular", "lingual", "cervical"]

CONDITIONS = [
    "caries",
    "fracture",
    "restoration",
    "crown",
    "extraction",
    "implant",
    "root_canal",
    "sealant",
]


def random_patient_id(patient_ids: list[str]) -> str:
    """Pick a random patient ID from the VU's tenant pool."""
    return random.choice(patient_ids)


def random_doctor_id(doctor_ids: list[str]) -> str:
    """Pick a random doctor ID from the VU's tenant pool."""
    return random.choice(doctor_ids)


def random_search_prefix() -> str:
    """Pick a random 2-char Colombian name prefix for patient search."""
    return random.choice(SEARCH_PREFIXES)


def random_tooth() -> str:
    """Pick a random FDI tooth number (11-48)."""
    return random.choice(FDI_TEETH)


def random_zone() -> str:
    """Pick a random tooth zone."""
    return random.choice(ZONES)


def random_condition() -> str:
    """Pick a random dental condition."""
    return random.choice(CONDITIONS)


def random_bulk_conditions(count: int = 8) -> list[dict]:
    """Generate a list of random odontogram conditions for bulk write."""
    conditions = []
    used_teeth = set()
    for _ in range(count):
        tooth = random_tooth()
        while tooth in used_teeth:
            tooth = random_tooth()
        used_teeth.add(tooth)
        conditions.append({
            "tooth_number": tooth,
            "zone": random_zone(),
            "condition": random_condition(),
            "notes": f"Load test condition for tooth {tooth}",
        })
    return conditions


def random_future_date(days_ahead_min: int = 1, days_ahead_max: int = 30) -> str:
    """Generate a random future date string (YYYY-MM-DD)."""
    offset = random.randint(days_ahead_min, days_ahead_max)
    future = date.today() + timedelta(days=offset)
    return future.isoformat()


def random_time_slot() -> str:
    """Generate a random appointment time slot (HH:MM) during business hours."""
    hour = random.randint(8, 17)
    minute = random.choice([0, 15, 30, 45])
    return f"{hour:02d}:{minute:02d}"


def random_colombian_cedula() -> str:
    """Generate a random Colombian cedula (8-10 digits)."""
    length = random.randint(8, 10)
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def random_patient_payload() -> dict:
    """Generate a random patient creation payload."""
    first_names = [
        "María", "Carlos", "Sofía", "Andrés", "Valentina",
        "Juan", "Isabela", "Santiago", "Camila", "Daniel",
        "Laura", "Felipe", "Natalia", "Sebastián", "Gabriela",
    ]
    last_names = [
        "González", "Rodríguez", "Martínez", "López", "Hernández",
        "García", "Morales", "Torres", "Ramírez", "Sánchez",
        "Vargas", "Ospina", "Castro", "Jiménez", "Reyes",
    ]
    return {
        "first_name": random.choice(first_names),
        "last_name": f"{random.choice(last_names)} {random.choice(last_names)}",
        "document_type": "CC",
        "document_number": random_colombian_cedula(),
        "birthdate": f"{random.randint(1960, 2005)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        "gender": random.choice(["male", "female"]),
        "phone": f"+573{random.randint(0, 9)}{random.randint(10000000, 99999999)}",
        "email": f"load_{uuid.uuid4().hex[:8]}@test.dentalos.co",
        "address": f"Cra {random.randint(1, 100)} # {random.randint(1, 200)}-{random.randint(1, 99)}, Bogotá",
        "blood_type": random.choice(["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]),
    }


def random_appointment_payload(doctor_id: str, patient_id: str) -> dict:
    """Generate a random appointment creation payload."""
    return {
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "date": random_future_date(),
        "start_time": random_time_slot(),
        "duration_minutes": random.choice([15, 30, 45, 60]),
        "type": random.choice(["consultation", "procedure", "follow_up", "emergency"]),
        "notes": "Load test appointment",
    }
