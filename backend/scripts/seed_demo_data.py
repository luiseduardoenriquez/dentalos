"""Seed comprehensive demo data for ALL DentalOS modules.

Run AFTER seed_dev.py has created the baseline (plans, tenant, users, patients).
This script fills every module with realistic Colombian dental clinic data so
every page can be visually evaluated.

Usage:
    cd backend
    python scripts/seed_demo_data.py

All dates use CURRENT_DATE arithmetic so the demo always looks current.
"""

import asyncio
import os
import sys

# Add backend/ to the Python path so `app` is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEMO_SCHEMA = "tn_demodent"

USER_EMAILS = [
    "owner@demo.dentalos.co",
    "doctor@demo.dentalos.co",
    "assistant@demo.dentalos.co",
    "receptionist@demo.dentalos.co",
]

PATIENT_DOCS = ["52814763", "80295143", "1020345678", "71634892", "1013598427"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def _print_ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _print_skip(msg: str) -> None:
    print(f"  [--] {msg} (skipped)")


async def _set_path(db: AsyncSession) -> None:
    """(Re-)set the search_path. Call after every commit / rollback."""
    await db.execute(text(f"SET search_path TO {DEMO_SCHEMA}, public"))


async def _commit(db: AsyncSession) -> None:
    """Commit and re-set search_path (asyncpg resets session state on commit)."""
    await db.commit()
    await _set_path(db)


async def _rollback(db: AsyncSession) -> None:
    """Rollback and re-set search_path."""
    await db.rollback()
    await _set_path(db)


async def _table_exists(db: AsyncSession, table: str) -> bool:
    """Check if a table exists in the tenant schema using information_schema."""
    result = await db.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables"
            "  WHERE table_schema = :schema AND table_name = :tbl"
            ")"
        ),
        {"schema": DEMO_SCHEMA, "tbl": table},
    )
    return result.scalar_one()


async def _row_exists(db: AsyncSession, query: str, params: dict) -> bool:
    result = await db.execute(text(query), params)
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Wave 0: Resolve existing IDs
# ---------------------------------------------------------------------------


async def wave_0_resolve_ids(db: AsyncSession) -> dict:
    """Resolve existing user and patient UUIDs from seed_dev.py data."""
    _print_section("Wave 0: Resolve existing IDs")
    ids: dict = {"users": {}, "patients": {}}

    # Users
    for email in USER_EMAILS:
        row = await db.execute(
            text("SELECT id FROM users WHERE email = :e"), {"e": email}
        )
        uid = row.scalar_one_or_none()
        if uid:
            key = email.split("@")[0]  # owner, doctor, assistant, receptionist
            ids["users"][key] = str(uid)
            _print_ok(f"User {email} -> {uid}")
        else:
            _print_skip(f"User {email} not found")

    # Patients
    names = ["maria", "carlos", "sofia", "luis", "isabela"]
    for doc, name in zip(PATIENT_DOCS, names):
        row = await db.execute(
            text("SELECT id FROM patients WHERE document_number = :d"), {"d": doc}
        )
        pid = row.scalar_one_or_none()
        if pid:
            ids["patients"][name] = str(pid)
            _print_ok(f"Patient {name} (doc={doc}) -> {pid}")
        else:
            _print_skip(f"Patient {name} (doc={doc}) not found")

    return ids


# ---------------------------------------------------------------------------
# Wave 1: Root / config data
# ---------------------------------------------------------------------------


async def wave_1_config(db: AsyncSession, ids: dict) -> dict:
    """Insert service_catalog, consent_templates, dental_labs, reminder_configs."""
    _print_section("Wave 1: Config & catalog data")
    w = {}

    # -- service_catalog (18 services with real CUPS codes) --
    if not await _table_exists(db, "service_catalog"):
        _print_skip("service_catalog table not found")
    else:
        services = [
            ("990201", "Consulta odontológica general", 8000000, "diagnostic"),
            ("990202", "Consulta odontológica especializada", 12000000, "diagnostic"),
            ("997120", "Profilaxis dental", 15000000, "preventive"),
            ("997110", "Detartraje supragingival", 12000000, "preventive"),
            ("997310", "Resina compuesta (1 superficie)", 18000000, "restorative"),
            ("997311", "Resina compuesta (2 superficies)", 25000000, "restorative"),
            ("997312", "Resina compuesta (3+ superficies)", 32000000, "restorative"),
            ("997410", "Endodoncia unirradicular", 45000000, "endodontic"),
            ("997411", "Endodoncia birradicular", 55000000, "endodontic"),
            ("997412", "Endodoncia multirradicular", 70000000, "endodontic"),
            ("997510", "Exodoncia simple", 15000000, "surgical"),
            ("997520", "Exodoncia quirúrgica", 35000000, "surgical"),
            ("997610", "Corona cerámica", 85000000, "prosthodontic"),
            ("997620", "Prótesis parcial removible", 120000000, "prosthodontic"),
            ("997710", "Sellante de fosas y fisuras", 8000000, "preventive"),
            ("997130", "Aplicación tópica de flúor", 6000000, "preventive"),
            ("997810", "Blanqueamiento dental", 50000000, "other"),
            ("997210", "Radiografía periapical", 5000000, "diagnostic"),
        ]
        svc_ids = {}
        for cups, name, price, cat in services:
            if await _row_exists(
                db,
                "SELECT id FROM service_catalog WHERE cups_code = :c",
                {"c": cups},
            ):
                row = await db.execute(
                    text("SELECT id FROM service_catalog WHERE cups_code = :c"),
                    {"c": cups},
                )
                svc_ids[cups] = str(row.scalar_one())
                continue
            row = await db.execute(
                text(
                    """INSERT INTO service_catalog
                       (id, cups_code, name, default_price, category, is_active, created_at, updated_at)
                       VALUES (gen_random_uuid(), :cups, :name, :price, :cat, true, now(), now())
                       RETURNING id"""
                ),
                {"cups": cups, "name": name, "price": price, "cat": cat},
            )
            svc_ids[cups] = str(row.mappings().first()["id"])
        await _commit(db)
        w["services"] = svc_ids
        _print_ok(f"Service catalog: {len(svc_ids)} services")

    # -- consent_templates (3) --
    if await _table_exists(db, "consent_templates"):
        ct_ids = {}
        templates = [
            ("Consentimiento General de Tratamiento", "general", 1),
            ("Consentimiento para Cirugía Oral", "surgery", 1),
            ("Consentimiento para Endodoncia", "endodontics", 1),
        ]
        for name, cat, ver in templates:
            if await _row_exists(
                db,
                "SELECT id FROM consent_templates WHERE name = :n",
                {"n": name},
            ):
                row = await db.execute(
                    text("SELECT id FROM consent_templates WHERE name = :n"),
                    {"n": name},
                )
                ct_ids[cat] = str(row.scalar_one())
                continue
            desc_text = f"Plantilla estándar para procedimientos de {cat}"
            content_text = (
                "Yo, [NOMBRE_PACIENTE], identificado(a) con [TIPO_DOC] No. [NUM_DOC], "
                f"autorizo al Dr(a). [NOMBRE_DOCTOR] para realizar el procedimiento de {cat}. "
                "He sido informado(a) de los riesgos, beneficios y alternativas."
            )
            row = await db.execute(
                text(
                    """INSERT INTO consent_templates
                       (id, name, category, description, content, version, is_active, created_at, updated_at)
                       VALUES (gen_random_uuid(), :name, :cat, :desc, :content, :ver, true, now(), now())
                       RETURNING id"""
                ),
                {"name": name, "cat": cat, "desc": desc_text, "content": content_text, "ver": ver},
            )
            ct_ids[cat] = str(row.mappings().first()["id"])
        await _commit(db)
        w["consent_templates"] = ct_ids
        _print_ok(f"Consent templates: {len(ct_ids)}")

    # -- dental_labs (2) --
    if await _table_exists(db, "dental_labs"):
        lab_ids = {}
        labs = [
            ("Laboratorio Dental Precisión", "Carlos Muñoz", "+5716345678", "Bogotá"),
            ("DentalTech Colombia", "Ana Ramírez", "+5716789012", "Medellín"),
        ]
        for name, contact, phone, city in labs:
            if await _row_exists(
                db,
                "SELECT id FROM dental_labs WHERE name = :n",
                {"n": name},
            ):
                row = await db.execute(
                    text("SELECT id FROM dental_labs WHERE name = :n"), {"n": name}
                )
                lab_ids[name] = str(row.scalar_one())
                continue
            row = await db.execute(
                text(
                    """INSERT INTO dental_labs
                       (id, name, contact_name, phone, city, is_active, created_at, updated_at)
                       VALUES (gen_random_uuid(), :name, :contact, :phone, :city, true, now(), now())
                       RETURNING id"""
                ),
                {"name": name, "contact": contact, "phone": phone, "city": city},
            )
            lab_ids[name] = str(row.mappings().first()["id"])
        await _commit(db)
        w["labs"] = lab_ids
        _print_ok(f"Dental labs: {len(lab_ids)}")

    # -- reminder_configs (1) --
    if await _table_exists(db, "reminder_configs"):
        if not await _row_exists(
            db, "SELECT id FROM reminder_configs LIMIT 1", {}
        ):
            await db.execute(
                text(
                    """INSERT INTO reminder_configs
                       (id, reminders, default_channels, max_reminders_allowed, created_at, updated_at)
                       VALUES (gen_random_uuid(),
                       '[{"hours_before": 24, "channel": "whatsapp"}, {"hours_before": 2, "channel": "sms"}]'::jsonb,
                       '["whatsapp", "sms"]'::jsonb,
                       3, now(), now())"""
                )
            )
            await _commit(db)
            _print_ok("Reminder config created")

    return w


# ---------------------------------------------------------------------------
# Wave 2: User/config-dependent data
# ---------------------------------------------------------------------------


async def wave_2_user_config(db: AsyncSession, ids: dict) -> dict:
    """Insert doctor_schedules, availability_blocks, notifications, cash_registers, intake_form_templates."""
    _print_section("Wave 2: User/config-dependent data")
    w = {}
    doctor_id = ids["users"].get("doctor")
    owner_id = ids["users"].get("owner")
    receptionist_id = ids["users"].get("receptionist")

    # -- doctor_schedules (Mon-Fri for doctor) --
    if await _table_exists(db, "doctor_schedules") and doctor_id:
        for day in range(0, 5):  # Mon=0 .. Fri=4
            if not await _row_exists(
                db,
                "SELECT id FROM doctor_schedules WHERE user_id = :uid AND day_of_week = :d",
                {"uid": doctor_id, "d": day},
            ):
                await db.execute(
                    text(
                        """INSERT INTO doctor_schedules
                           (id, user_id, day_of_week, is_working, start_time, end_time, breaks, created_at, updated_at)
                           VALUES (gen_random_uuid(), :uid, :d, true, '08:00', '18:00',
                           '[{"start": "12:00", "end": "13:00"}]'::jsonb, now(), now())"""
                    ),
                    {"uid": doctor_id, "d": day},
                )
        # Sat
        if not await _row_exists(
            db,
            "SELECT id FROM doctor_schedules WHERE user_id = :uid AND day_of_week = 5",
            {"uid": doctor_id},
        ):
            await db.execute(
                text(
                    """INSERT INTO doctor_schedules
                       (id, user_id, day_of_week, is_working, start_time, end_time, breaks, created_at, updated_at)
                       VALUES (gen_random_uuid(), :uid, 5, true, '08:00', '13:00', '[]'::jsonb, now(), now())"""
                ),
                {"uid": doctor_id},
            )
        # Sun
        if not await _row_exists(
            db,
            "SELECT id FROM doctor_schedules WHERE user_id = :uid AND day_of_week = 6",
            {"uid": doctor_id},
        ):
            await db.execute(
                text(
                    """INSERT INTO doctor_schedules
                       (id, user_id, day_of_week, is_working, start_time, end_time, created_at, updated_at)
                       VALUES (gen_random_uuid(), :uid, 6, false, NULL, NULL, now(), now())"""
                ),
                {"uid": doctor_id},
            )
        await _commit(db)
        _print_ok("Doctor schedules (7 days)")

    # -- availability_blocks (1 vacation block next month) --
    if await _table_exists(db, "availability_blocks") and doctor_id:
        if not await _row_exists(
            db,
            "SELECT id FROM availability_blocks WHERE doctor_id = :d AND reason = 'vacation'",
            {"d": doctor_id},
        ):
            await db.execute(
                text(
                    """INSERT INTO availability_blocks
                       (id, doctor_id, start_time, end_time, reason, description,
                        is_recurring, is_active, created_at, updated_at)
                       VALUES (gen_random_uuid(), :d,
                       CURRENT_DATE + interval '30 days' + interval '8 hours',
                       CURRENT_DATE + interval '33 days' + interval '18 hours',
                       'vacation', 'Vacaciones programadas', false, true, now(), now())"""
                ),
                {"d": doctor_id},
            )
            await _commit(db)
            _print_ok("Availability block (vacation)")

    # -- notifications (5 for owner) --
    if await _table_exists(db, "notifications") and owner_id:
        notif_count = await db.execute(
            text("SELECT count(*) FROM notifications WHERE user_id = :u"),
            {"u": owner_id},
        )
        if notif_count.scalar_one() < 3:
            notifs = [
                ("appointment_reminder", "Recordatorio de cita", "María González tiene cita hoy a las 9:00 AM"),
                ("payment_received", "Pago recibido", "Se registró un pago de $150,000 COP de Carlos Martínez"),
                ("new_patient", "Nuevo paciente registrado", "Isabela Sánchez se registró por el portal del paciente"),
                ("lab_order_ready", "Orden de laboratorio lista", "La corona cerámica para María González está lista para recoger"),
                ("task_assigned", "Tarea asignada", "Se le asignó la tarea: Llamar a paciente Luis Jiménez para confirmar cita"),
            ]
            for ntype, title, body in notifs:
                await db.execute(
                    text(
                        """INSERT INTO notifications
                           (id, user_id, type, title, body, meta_data, is_active, created_at, updated_at)
                           VALUES (gen_random_uuid(), :uid, :t, :title, :body, '{}'::jsonb, true,
                           now() - (random() * interval '48 hours'), now())"""
                    ),
                    {"uid": owner_id, "t": ntype, "title": title, "body": body},
                )
            await _commit(db)
            _print_ok("Notifications: 5")

    # -- cash_registers (1 open) --
    if await _table_exists(db, "cash_registers") and receptionist_id:
        if not await _row_exists(
            db,
            "SELECT id FROM cash_registers WHERE name = 'Caja Principal'",
            {},
        ):
            row = await db.execute(
                text(
                    """INSERT INTO cash_registers
                       (id, name, location, status, opened_by, opened_at,
                        opening_balance_cents, created_at, updated_at)
                       VALUES (gen_random_uuid(), 'Caja Principal', 'Recepción',
                       'open', :uid, CURRENT_DATE + interval '7 hours',
                       50000000, now(), now())
                       RETURNING id"""
                ),
                {"uid": receptionist_id},
            )
            w["cash_register_id"] = str(row.mappings().first()["id"])
            await _commit(db)
            _print_ok("Cash register: Caja Principal (open)")
        else:
            row = await db.execute(text("SELECT id FROM cash_registers WHERE name = 'Caja Principal'"))
            w["cash_register_id"] = str(row.scalar_one())
            _print_skip("Cash register already exists, resolved ID")

    # -- intake_form_templates (1) --
    if await _table_exists(db, "intake_form_templates") and owner_id:
        if not await _row_exists(
            db,
            "SELECT id FROM intake_form_templates WHERE name = 'Formulario de ingreso estándar'",
            {},
        ):
            row = await db.execute(
                text(
                    """INSERT INTO intake_form_templates
                       (id, name, fields, is_default, is_active, created_by, created_at, updated_at)
                       VALUES (gen_random_uuid(), 'Formulario de ingreso estándar',
                       '[{"name": "motivo_consulta", "type": "text", "label": "Motivo de consulta", "required": true},
                         {"name": "alergias", "type": "text", "label": "Alergias conocidas", "required": false},
                         {"name": "medicamentos", "type": "text", "label": "Medicamentos actuales", "required": false},
                         {"name": "embarazo", "type": "boolean", "label": "¿Está embarazada?", "required": false}]'::jsonb,
                       true, true, :uid, now(), now())
                       RETURNING id"""
                ),
                {"uid": owner_id},
            )
            w["intake_template_id"] = str(row.mappings().first()["id"])
            await _commit(db)
            _print_ok("Intake form template")
        else:
            row = await db.execute(
                text("SELECT id FROM intake_form_templates WHERE name = 'Formulario de ingreso estándar'")
            )
            w["intake_template_id"] = str(row.scalar_one())
            _print_skip("Intake template already exists, resolved ID")

    return w


# ---------------------------------------------------------------------------
# Wave 3: Patient clinical + operational
# ---------------------------------------------------------------------------


async def wave_3_clinical(db: AsyncSession, ids: dict, w1: dict) -> dict:
    """Insert anamnesis, clinical_records, odontogram, diagnoses, treatment_plans,
    consents, loyalty, referrals, families, tasks, eps, whatsapp, periodontal, calls, expenses."""
    _print_section("Wave 3: Clinical & operational data")
    w = {}
    doctor_id = ids["users"].get("doctor")
    owner_id = ids["users"].get("owner")
    receptionist_id = ids["users"].get("receptionist")
    maria = ids["patients"].get("maria")
    carlos = ids["patients"].get("carlos")
    sofia = ids["patients"].get("sofia")
    luis = ids["patients"].get("luis")
    isabela = ids["patients"].get("isabela")

    if not doctor_id or not maria:
        _print_skip("Missing doctor or patient IDs")
        return w

    # -- anamnesis (3 patients) --
    if await _table_exists(db, "anamnesis"):
        for pid, allergies, meds in [
            (maria, '["Penicilina"]', '["Ibuprofeno 400mg"]'),
            (carlos, '[]', '["Losartán 50mg", "Metformina 850mg"]'),
            (sofia, '["Látex"]', '[]'),
        ]:
            if not await _row_exists(
                db,
                "SELECT id FROM anamnesis WHERE patient_id = :p",
                {"p": pid},
            ):
                await db.execute(
                    text(
                        """INSERT INTO anamnesis
                           (id, patient_id, allergies, medications, medical_history,
                            dental_history, last_updated_by, is_active, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid,
                           CAST(:allergies AS jsonb), CAST(:meds AS jsonb),
                           '{"diabetes": false, "hipertension": false, "cardiopatia": false}'::jsonb,
                           '{"ultima_visita": "hace 6 meses", "tratamiento_previo": "profilaxis"}'::jsonb,
                           :doc, true, now(), now())"""
                    ),
                    {"pid": pid, "allergies": allergies, "meds": meds, "doc": doctor_id},
                )
        await _commit(db)
        _print_ok("Anamnesis: 3 patients")

    # -- clinical_records (3) --
    cr_ids = {}
    if await _table_exists(db, "clinical_records"):
        records = [
            (maria, "examination", '{"motivo": "Control periódico", "hallazgos": "Caries en 36 mesial, acumulación de cálculo en sector anterior inferior", "plan": "Profilaxis + resina 36"}'),
            (carlos, "evolution_note", '{"procedimiento": "Profilaxis dental completa", "observaciones": "Paciente refiere sensibilidad al frío en 14. Se recomienda evaluación endodóntica", "siguiente_cita": "Control en 6 meses"}'),
            (sofia, "procedure", '{"procedimiento": "Resina compuesta 46 oclusal", "material": "Resina 3M Z350 A2", "anestesia": "Lidocaína 2% con epinefrina", "tiempo": "45 minutos", "resultado": "Satisfactorio"}'),
        ]
        for pid, rtype, content in records:
            if not await _row_exists(
                db,
                "SELECT id FROM clinical_records WHERE patient_id = :p AND type = :t LIMIT 1",
                {"p": pid, "t": rtype},
            ):
                row = await db.execute(
                    text(
                        """INSERT INTO clinical_records
                           (id, patient_id, doctor_id, type, content, is_editable, is_active, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :doc, :t, CAST(:c AS jsonb), true, true,
                           now() - interval '7 days', now())
                           RETURNING id"""
                    ),
                    {"pid": pid, "doc": doctor_id, "t": rtype, "c": content},
                )
                cr_ids[f"{pid}_{rtype}"] = str(row.mappings().first()["id"])
        await _commit(db)
        _print_ok(f"Clinical records: {len(cr_ids)}")

    # -- odontogram_states (3 patients) --
    if await _table_exists(db, "odontogram_states"):
        for pid in [maria, carlos, sofia]:
            if not await _row_exists(
                db,
                "SELECT id FROM odontogram_states WHERE patient_id = :p",
                {"p": pid},
            ):
                await db.execute(
                    text(
                        """INSERT INTO odontogram_states
                           (id, patient_id, dentition_type, is_active, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, 'adult', true, now(), now())"""
                    ),
                    {"pid": pid},
                )
        await _commit(db)
        _print_ok("Odontogram states: 3")

    # -- odontogram_conditions (10) --
    if await _table_exists(db, "odontogram_conditions"):
        conditions = [
            (maria, 36, "mesial", "caries", "moderate"),
            (maria, 46, "oclusal", "restoration", None),
            (maria, 18, "full", "absent", None),
            (carlos, 14, "full", "endodontic", None),
            (carlos, 15, "full", "crown", None),
            (carlos, 28, "full", "absent", None),
            (carlos, 38, "full", "absent", None),
            (sofia, 46, "oclusal", "restoration", None),
            (sofia, 26, "oclusal", "sealant", None),
            (sofia, 11, "incisal", "fracture", "mild"),
        ]
        for pid, tooth, zone, code, sev in conditions:
            if not await _row_exists(
                db,
                "SELECT id FROM odontogram_conditions WHERE patient_id = :p AND tooth_number = :t AND zone = :z",
                {"p": pid, "t": tooth, "z": zone},
            ):
                await db.execute(
                    text(
                        """INSERT INTO odontogram_conditions
                           (id, patient_id, tooth_number, zone, condition_code, severity,
                            source, created_by, is_active, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :tooth, :zone, :code, :sev,
                           'manual', :doc, true, now(), now())"""
                    ),
                    {"pid": pid, "tooth": tooth, "zone": zone, "code": code, "sev": sev, "doc": doctor_id},
                )
        await _commit(db)
        _print_ok("Odontogram conditions: 10")

    # -- diagnoses (3) --
    if await _table_exists(db, "diagnoses"):
        diags = [
            (maria, "K02.1", "Caries de la dentina", "moderate", "active", 36),
            (carlos, "K04.0", "Pulpitis", "severe", "resolved", 14),
            (sofia, "S02.5", "Fractura de diente", "mild", "active", 11),
        ]
        for pid, cie, desc, sev, status, tooth in diags:
            if not await _row_exists(
                db,
                "SELECT id FROM diagnoses WHERE patient_id = :p AND cie10_code = :c",
                {"p": pid, "c": cie},
            ):
                await db.execute(
                    text(
                        """INSERT INTO diagnoses
                           (id, patient_id, doctor_id, cie10_code, cie10_description,
                            severity, status, tooth_number, is_active, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :doc, :cie, :desc,
                           :sev, :status, :tooth, true, now() - interval '10 days', now())"""
                    ),
                    {"pid": pid, "doc": doctor_id, "cie": cie, "desc": desc,
                     "sev": sev, "status": status, "tooth": tooth},
                )
        await _commit(db)
        _print_ok("Diagnoses: 3")

    # -- treatment_plans (2) --
    tp_ids = {}
    if await _table_exists(db, "treatment_plans"):
        plans = [
            (maria, "Plan de tratamiento María - Restauración y profilaxis", "active", 5100000, 0),
            (carlos, "Plan de tratamiento Carlos - Endodoncia y corona", "completed", 13000000, 13000000),
        ]
        for pid, name, status, est, actual in plans:
            if not await _row_exists(
                db,
                "SELECT id FROM treatment_plans WHERE patient_id = :p AND name = :n",
                {"p": pid, "n": name},
            ):
                row = await db.execute(
                    text(
                        """INSERT INTO treatment_plans
                           (id, patient_id, doctor_id, name, status,
                            total_cost_estimated, total_cost_actual, is_active, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :doc, :name, :status,
                           :est, :actual, true, now() - interval '14 days', now())
                           RETURNING id"""
                    ),
                    {"pid": pid, "doc": doctor_id, "name": name, "status": status,
                     "est": est, "actual": actual},
                )
                key = "maria_tp" if pid == maria else "carlos_tp"
                tp_ids[key] = str(row.mappings().first()["id"])
        await _commit(db)
        w["treatment_plans"] = tp_ids
        _print_ok(f"Treatment plans: {len(tp_ids)}")

    # -- consents (2) --
    if await _table_exists(db, "consents"):
        consent_data = [
            (maria, "Consentimiento tratamiento restaurador", "signed"),
            (carlos, "Consentimiento endodoncia pieza 14", "signed"),
        ]
        for pid, title, status in consent_data:
            if not await _row_exists(
                db,
                "SELECT id FROM consents WHERE patient_id = :p AND title = :t",
                {"p": pid, "t": title},
            ):
                await db.execute(
                    text(
                        """INSERT INTO consents
                           (id, patient_id, doctor_id, title, content_rendered, status,
                            signed_at, is_active, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :doc, :title,
                           'Autorizo el procedimiento descrito. He sido informado(a) de riesgos y alternativas.',
                           :status, now() - interval '12 days', true,
                           now() - interval '14 days', now())"""
                    ),
                    {"pid": pid, "doc": doctor_id, "title": title, "status": status},
                )
        await _commit(db)
        _print_ok("Consents: 2")

    # -- loyalty_points (3 patients) --
    if await _table_exists(db, "loyalty_points"):
        for pid, balance, earned, redeemed in [
            (maria, 150, 200, 50),
            (carlos, 320, 320, 0),
            (sofia, 80, 80, 0),
        ]:
            if not await _row_exists(
                db,
                "SELECT id FROM loyalty_points WHERE patient_id = :p",
                {"p": pid},
            ):
                await db.execute(
                    text(
                        """INSERT INTO loyalty_points
                           (id, patient_id, points_balance, lifetime_points_earned,
                            lifetime_points_redeemed, last_activity_at, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :bal, :earned, :redeemed, now(), now(), now())"""
                    ),
                    {"pid": pid, "bal": balance, "earned": earned, "redeemed": redeemed},
                )
        await _commit(db)
        _print_ok("Loyalty points: 3")

    # -- referral_codes (2) --
    ref_ids = {}
    if await _table_exists(db, "referral_codes"):
        for pid, code in [(maria, "MARIA25"), (carlos, "CARL100")]:
            if not await _row_exists(
                db,
                "SELECT id FROM referral_codes WHERE code = :c",
                {"c": code},
            ):
                row = await db.execute(
                    text(
                        """INSERT INTO referral_codes
                           (id, patient_id, code, is_active, uses_count, max_uses, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :code, true, 1, 10, now(), now())
                           RETURNING id"""
                    ),
                    {"pid": pid, "code": code},
                )
                ref_ids[code] = str(row.mappings().first()["id"])
        await _commit(db)
        w["referral_codes"] = ref_ids
        _print_ok("Referral codes: 2")

    # -- family_groups + family_members --
    if await _table_exists(db, "family_groups") and maria and isabela:
        if not await _row_exists(
            db,
            "SELECT id FROM family_groups WHERE name = 'Familia González'",
            {},
        ):
            row = await db.execute(
                text(
                    """INSERT INTO family_groups
                       (id, name, primary_contact_patient_id, is_active, created_at, updated_at)
                       VALUES (gen_random_uuid(), 'Familia González', :maria, true, now(), now())
                       RETURNING id"""
                ),
                {"maria": maria},
            )
            fg_id = str(row.mappings().first()["id"])
            # Add family members
            if await _table_exists(db, "family_members"):
                for pid, rel in [(maria, "parent"), (isabela, "child")]:
                    if not await _row_exists(
                        db,
                        "SELECT id FROM family_members WHERE patient_id = :p",
                        {"p": pid},
                    ):
                        await db.execute(
                            text(
                                """INSERT INTO family_members
                                   (id, family_group_id, patient_id, relationship, is_active, created_at, updated_at)
                                   VALUES (gen_random_uuid(), :fg, :pid, :rel, true, now(), now())"""
                            ),
                            {"fg": fg_id, "pid": pid, "rel": rel},
                        )
            await _commit(db)
            _print_ok("Family group: Familia González (2 members)")

    # -- staff_tasks (4) --
    if await _table_exists(db, "staff_tasks") and receptionist_id:
        tasks = [
            ("Llamar a Luis Jiménez para confirmar cita", "manual", "open", "high", receptionist_id, luis),
            ("Cobro pendiente factura María González", "delinquency", "open", "urgent", receptionist_id, maria),
            ("Verificar EPS de Sofía Hernández", "manual", "in_progress", "normal", receptionist_id, sofia),
            ("Seguimiento post-operatorio Carlos Martínez", "manual", "completed", "normal", doctor_id, carlos),
        ]
        for title, ttype, status, priority, assigned, patient_id in tasks:
            if not await _row_exists(
                db,
                "SELECT id FROM staff_tasks WHERE title = :t",
                {"t": title},
            ):
                await db.execute(
                    text(
                        """INSERT INTO staff_tasks
                           (id, title, task_type, status, priority, assigned_to, patient_id,
                            due_date, created_at, updated_at)
                           VALUES (gen_random_uuid(), :title, :ttype, :status, :priority,
                           :assigned, :pid, CURRENT_DATE + interval '3 days', now(), now())"""
                    ),
                    {"title": title, "ttype": ttype, "status": status, "priority": priority,
                     "assigned": assigned, "pid": patient_id},
                )
        await _commit(db)
        _print_ok("Staff tasks: 4")

    # -- eps_verifications (2) --
    if await _table_exists(db, "eps_verifications"):
        for pid, eps_name, eps_code, status, regime in [
            (maria, "Sura EPS", "EPS016", "activo", "contributivo"),
            (carlos, "Nueva EPS", "EPS037", "activo", "contributivo"),
        ]:
            if not await _row_exists(
                db,
                "SELECT id FROM eps_verifications WHERE patient_id = :p",
                {"p": pid},
            ):
                await db.execute(
                    text(
                        """INSERT INTO eps_verifications
                           (id, patient_id, eps_name, eps_code, affiliation_status, regime,
                            copay_category, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :eps, :code, :status, :regime,
                           'B', now(), now())"""
                    ),
                    {"pid": pid, "eps": eps_name, "code": eps_code,
                     "status": status, "regime": regime},
                )
        await _commit(db)
        _print_ok("EPS verifications: 2")

    # -- whatsapp_conversations (3) + messages (wave 5) --
    wa_ids = {}
    if await _table_exists(db, "whatsapp_conversations"):
        convos = [
            (maria, "+5716234567", "active", receptionist_id),
            (carlos, "+5716891234", "active", doctor_id),
            (sofia, "+5716452890", "archived", receptionist_id),
        ]
        for pid, phone, status, assigned in convos:
            if not await _row_exists(
                db,
                "SELECT id FROM whatsapp_conversations WHERE phone_number = :p",
                {"p": phone},
            ):
                row = await db.execute(
                    text(
                        """INSERT INTO whatsapp_conversations
                           (id, patient_id, phone_number, status, assigned_to,
                            last_message_at, unread_count, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :phone, :status, :assigned,
                           now() - interval '2 hours', :unread, now(), now())
                           RETURNING id"""
                    ),
                    {"pid": pid, "phone": phone, "status": status,
                     "assigned": assigned, "unread": 2 if status == "active" else 0},
                )
                wa_ids[phone] = str(row.mappings().first()["id"])
        await _commit(db)
        w["whatsapp_conversations"] = wa_ids
        _print_ok(f"WhatsApp conversations: {len(wa_ids)}")

    # -- periodontal_records + measurements --
    if await _table_exists(db, "periodontal_records") and maria:
        if not await _row_exists(
            db,
            "SELECT id FROM periodontal_records WHERE patient_id = :p",
            {"p": maria},
        ):
            row = await db.execute(
                text(
                    """INSERT INTO periodontal_records
                       (id, patient_id, recorded_by, dentition_type, source, notes,
                        is_active, created_at, updated_at)
                       VALUES (gen_random_uuid(), :pid, :doc, 'adult', 'manual',
                       'Evaluación periodontal inicial. Acumulación de cálculo sector anterior inferior.',
                       true, now(), now())
                       RETURNING id"""
                ),
                {"pid": maria, "doc": doctor_id},
            )
            perio_id = str(row.mappings().first()["id"])
            # 12 measurements (teeth 11, 21 × 6 sites each)
            if await _table_exists(db, "periodontal_measurements"):
                sites = ["mesial_buccal", "buccal", "distal_buccal",
                         "mesial_lingual", "lingual", "distal_lingual"]
                for tooth in [11, 21]:
                    for site in sites:
                        pd = 3 if "buccal" in site else 2
                        bop = site in ("mesial_buccal", "mesial_lingual")
                        await db.execute(
                            text(
                                """INSERT INTO periodontal_measurements
                                   (id, record_id, tooth_number, site, pocket_depth,
                                    recession, bleeding_on_probing, plaque_index, created_at)
                                   VALUES (gen_random_uuid(), :rid, :tooth, :site, :pd,
                                   0, :bop, :plaque, now())"""
                            ),
                            {"rid": perio_id, "tooth": tooth, "site": site,
                             "pd": pd, "bop": bop, "plaque": site == "buccal"},
                        )
            await _commit(db)
            _print_ok("Periodontal record + 12 measurements")

    # -- call_logs (5) --
    if await _table_exists(db, "call_logs"):
        calls = [
            (maria, "+5716234567", "inbound", "completed", 180, receptionist_id, "Confirmó cita de mañana"),
            (carlos, "+5716891234", "outbound", "completed", 120, receptionist_id, "Recordatorio de pago"),
            (sofia, "+5716452890", "inbound", "missed", None, None, None),
            (luis, "+5716789012", "outbound", "completed", 90, receptionist_id, "Reagendó cita para la próxima semana"),
            (isabela, "+5716123456", "inbound", "completed", 60, receptionist_id, "Consulta sobre precios de blanqueamiento"),
        ]
        existing = await db.execute(text("SELECT count(*) FROM call_logs"))
        if existing.scalar_one() < 3:
            for pid, phone, direction, status, dur, staff, notes in calls:
                ended_expr = "now() - (random() * interval '47 hours')" if dur is not None else "NULL"
                await db.execute(
                    text(
                        f"""INSERT INTO call_logs
                           (id, patient_id, phone_number, direction, status,
                            duration_seconds, staff_id, notes,
                            started_at, ended_at, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :phone, :dir, :status,
                           :dur, :staff, :notes,
                           now() - (random() * interval '48 hours'),
                           {ended_expr},
                           now(), now())"""
                    ),
                    {"pid": pid, "phone": phone, "dir": direction, "status": status,
                     "dur": dur, "staff": staff, "notes": notes},
                )
            await _commit(db)
            _print_ok("Call logs: 5")

    # -- eps_claims (3) --
    if await _table_exists(db, "eps_claims"):
        existing = await db.execute(text("SELECT count(*) FROM eps_claims"))
        if existing.scalar_one() < 2:
            claims = [
                (maria, "EPS016", "Sura EPS", "dental", 4500000, 900000, "draft", None),
                (carlos, "EPS037", "Nueva EPS", "dental", 13000000, 2600000, "submitted", "now() - interval '5 days'"),
                (sofia, "EPS001", "Compensar", "dental", 1800000, 360000, "paid", "now() - interval '30 days'"),
            ]
            for pid, code, name, ctype, total, copay, status, submitted in claims:
                await db.execute(
                    text(
                        f"""INSERT INTO eps_claims
                           (id, patient_id, eps_code, eps_name, claim_type,
                            procedures, total_amount_cents, copay_amount_cents,
                            status, submitted_at, created_by, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :code, :name, :ctype,
                           '[{{"cups_code": "997310", "description": "Resina compuesta", "amount_cents": {total}}}]'::jsonb,
                           :total, :copay, :status,
                           {submitted if submitted else 'NULL'},
                           :doc, now(), now())"""
                    ),
                    {"pid": pid, "code": code, "name": name, "ctype": ctype,
                     "total": total, "copay": copay, "status": status, "doc": doctor_id},
                )
            await _commit(db)
            _print_ok("EPS claims: 3")

    # -- expenses (5) --
    if await _table_exists(db, "expenses") and await _table_exists(db, "expense_categories"):
        existing = await db.execute(text("SELECT count(*) FROM expenses"))
        if existing.scalar_one() < 3:
            expense_data = [
                ("Insumos", 35000000, "Compra resinas composite 3M", -10),
                ("Laboratorio", 85000000, "Corona cerámica Lab Precisión", -5),
                ("Servicios públicos", 45000000, "Factura energía eléctrica marzo", -3),
                ("Marketing", 15000000, "Pauta redes sociales marzo", -7),
                ("Equipos", 250000000, "Mantenimiento compresor dental", -20),
            ]
            for cat_name, amount, desc, days_offset in expense_data:
                cat_row = await db.execute(
                    text("SELECT id FROM expense_categories WHERE name = :n"),
                    {"n": cat_name},
                )
                cat_id = cat_row.scalar_one_or_none()
                if cat_id:
                    await db.execute(
                        text(
                            """INSERT INTO expenses
                               (id, category_id, amount_cents, description,
                                expense_date, recorded_by, is_active, created_at, updated_at)
                               VALUES (gen_random_uuid(), :cat, :amount, :desc,
                               CURRENT_DATE + :days * interval '1 day', :uid, true, now(), now())"""
                        ),
                        {"cat": str(cat_id), "amount": amount, "desc": desc,
                         "days": days_offset, "uid": owner_id},
                    )
            await _commit(db)
            _print_ok("Expenses: 5")

    return w


# ---------------------------------------------------------------------------
# Wave 4: Treatment plan items + lab orders
# ---------------------------------------------------------------------------


async def wave_4_tp_items(db: AsyncSession, ids: dict, w1: dict, w3: dict) -> dict:
    """Insert treatment_plan_items, lab_orders."""
    _print_section("Wave 4: Treatment plan items & lab orders")
    w = {}
    doctor_id = ids["users"].get("doctor")
    maria = ids["patients"].get("maria")
    carlos = ids["patients"].get("carlos")
    sofia = ids["patients"].get("sofia")
    tp_ids = w3.get("treatment_plans", {})
    lab_ids = w1.get("labs", {})

    # -- treatment_plan_items --
    if await _table_exists(db, "treatment_plan_items"):
        maria_tp = tp_ids.get("maria_tp")
        carlos_tp = tp_ids.get("carlos_tp")

        if maria_tp:
            items = [
                (maria_tp, "997120", "Profilaxis dental", None, 1500000, 0, 1, "pending"),
                (maria_tp, "997310", "Resina compuesta 36 mesial", 36, 1800000, 0, 2, "pending"),
                (maria_tp, "997310", "Resina compuesta 36 oclusal", 36, 1800000, 0, 3, "pending"),
            ]
            existing = await db.execute(
                text("SELECT count(*) FROM treatment_plan_items WHERE treatment_plan_id = :tp"),
                {"tp": maria_tp},
            )
            if existing.scalar_one() == 0:
                for tp, cups, desc, tooth, est, actual, order, status in items:
                    await db.execute(
                        text(
                            """INSERT INTO treatment_plan_items
                               (id, treatment_plan_id, cups_code, cups_description,
                                tooth_number, estimated_cost, actual_cost, priority_order,
                                status, created_at, updated_at)
                               VALUES (gen_random_uuid(), :tp, :cups, :desc, :tooth,
                               :est, :actual, :ord, :status, now(), now())"""
                        ),
                        {"tp": tp, "cups": cups, "desc": desc, "tooth": tooth,
                         "est": est, "actual": actual, "ord": order, "status": status},
                    )
                _print_ok("Treatment plan items (María): 3")

        if carlos_tp:
            items = [
                (carlos_tp, "997410", "Endodoncia unirradicular pieza 14", 14, 4500000, 4500000, 1, "completed"),
                (carlos_tp, "997610", "Corona cerámica pieza 14", 14, 8500000, 8500000, 2, "completed"),
            ]
            existing = await db.execute(
                text("SELECT count(*) FROM treatment_plan_items WHERE treatment_plan_id = :tp"),
                {"tp": carlos_tp},
            )
            if existing.scalar_one() == 0:
                for tp, cups, desc, tooth, est, actual, order, status in items:
                    await db.execute(
                        text(
                            """INSERT INTO treatment_plan_items
                               (id, treatment_plan_id, cups_code, cups_description,
                                tooth_number, estimated_cost, actual_cost, priority_order,
                                status, created_at, updated_at)
                               VALUES (gen_random_uuid(), :tp, :cups, :desc, :tooth,
                               :est, :actual, :ord, :status, now(), now())"""
                        ),
                        {"tp": tp, "cups": cups, "desc": desc, "tooth": tooth,
                         "est": est, "actual": actual, "ord": order, "status": status},
                    )
                _print_ok("Treatment plan items (Carlos): 2")

        await _commit(db)

    # -- lab_orders (3) --
    if await _table_exists(db, "lab_orders") and doctor_id:
        lab_name_1 = "Laboratorio Dental Precisión"
        lab_name_2 = "DentalTech Colombia"
        lab1 = lab_ids.get(lab_name_1)
        lab2 = lab_ids.get(lab_name_2)
        existing = await db.execute(text("SELECT count(*) FROM lab_orders"))
        if existing.scalar_one() < 2:
            orders = [
                (maria, lab1, "crown", "pending", None, None, None, 8500000,
                 '{"material": "Porcelana E.max", "color": "A2", "pieza": 36}'),
                (carlos, lab1, "crown", "delivered", "now()-interval '20 days'",
                 "now()-interval '5 days'", "now()-interval '2 days'", 8500000,
                 '{"material": "Zirconia", "color": "A3", "pieza": 14}'),
                (sofia, lab2, "retainer", "in_progress", "now()-interval '7 days'",
                 None, None, 4500000,
                 '{"tipo": "Hawley superior", "color_acrilico": "transparente"}'),
            ]
            for pid, lab, otype, status, sent, ready, delivered, cost, specs in orders:
                sent_sql = sent if sent else "NULL"
                ready_sql = ready if ready else "NULL"
                delivered_sql = delivered if delivered else "NULL"
                await db.execute(
                    text(
                        f"""INSERT INTO lab_orders
                           (id, patient_id, lab_id, order_type, status, specifications,
                            due_date, sent_at, ready_at, delivered_at, cost_cents, created_by,
                            is_active, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :lab, :otype, :status, CAST(:specs AS jsonb),
                           CURRENT_DATE + interval '14 days',
                           {sent_sql}, {ready_sql}, {delivered_sql},
                           :cost, :doc, true, now(), now())"""
                    ),
                    {"pid": pid, "lab": lab, "otype": otype, "status": status,
                     "specs": specs, "cost": cost, "doc": doctor_id},
                )
            await _commit(db)
            _print_ok("Lab orders: 3")

    return w


# ---------------------------------------------------------------------------
# Wave 5: Scheduling + communication
# ---------------------------------------------------------------------------


async def wave_5_appointments(db: AsyncSession, ids: dict, w1: dict, w2: dict, w3: dict) -> dict:
    """Insert appointments, quotations, prescriptions, intake_submissions,
    whatsapp_messages, nps_survey_responses, chatbot, email_campaigns."""
    _print_section("Wave 5: Appointments & communication")
    w = {}
    doctor_id = ids["users"].get("doctor")
    owner_id = ids["users"].get("owner")
    receptionist_id = ids["users"].get("receptionist")
    maria = ids["patients"].get("maria")
    carlos = ids["patients"].get("carlos")
    sofia = ids["patients"].get("sofia")
    luis = ids["patients"].get("luis")
    isabela = ids["patients"].get("isabela")

    if not doctor_id or not maria:
        _print_skip("Missing IDs")
        return w

    # -- appointments (10) --
    appt_ids = {}
    if await _table_exists(db, "appointments"):
        existing = await db.execute(text("SELECT count(*) FROM appointments"))
        if existing.scalar_one() < 5:
            appts = [
                # Today (3)
                (maria, 9, 30, "consultation", "confirmed"),
                (carlos, 10, 60, "procedure", "scheduled"),
                (sofia, 14, 30, "follow_up", "confirmed"),
                # Tomorrow (2)
                (luis, 9, 45, "consultation", "scheduled"),
                (isabela, 11, 30, "consultation", "scheduled"),
                # Past completed (2)
                (maria, -14*24, 30, "consultation", "completed"),
                (carlos, -7*24, 60, "procedure", "completed"),
                # No-show (1)
                (luis, -3*24, 30, "consultation", "no_show"),
                # Next week (2)
                (sofia, 7*24+10, 30, "follow_up", "scheduled"),
                (isabela, 7*24+14, 45, "procedure", "scheduled"),
            ]
            for i, (pid, hour_offset, dur, atype, status) in enumerate(appts):
                if hour_offset >= 0 and hour_offset < 24:
                    # Today
                    start_expr = f"CURRENT_DATE + interval '{hour_offset} hours'"
                elif hour_offset >= 24 and hour_offset < 48:
                    # Tomorrow
                    start_expr = f"CURRENT_DATE + interval '1 day' + interval '{hour_offset - 24} hours'"
                else:
                    # Relative hours (negative = past, large = future)
                    start_expr = f"CURRENT_TIMESTAMP + interval '{hour_offset} hours'"

                completed_expr = f"{start_expr} + interval '{dur} minutes'" if status == "completed" else "NULL"
                no_show_expr = f"{start_expr} + interval '15 minutes'" if status == "no_show" else "NULL"
                row = await db.execute(
                    text(
                        f"""INSERT INTO appointments
                           (id, patient_id, doctor_id, start_time, end_time,
                            duration_minutes, type, status, cancelled_by_patient,
                            created_by, is_active,
                            completed_at, no_show_at,
                            created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :doc,
                           {start_expr},
                           {start_expr} + interval '{dur} minutes',
                           :dur, :atype, :status, false, :created_by, true,
                           {completed_expr},
                           {no_show_expr},
                           now(), now())
                           RETURNING id"""
                    ),
                    {"pid": pid, "doc": doctor_id, "dur": dur, "atype": atype,
                     "status": status, "created_by": receptionist_id},
                )
                appt_ids[f"appt_{i}"] = str(row.mappings().first()["id"])
            await _commit(db)
            w["appointments"] = appt_ids
            _print_ok(f"Appointments: {len(appt_ids)}")

    # -- quotations (2) --
    quot_ids = {}
    if await _table_exists(db, "quotations"):
        existing = await db.execute(text("SELECT count(*) FROM quotations"))
        if existing.scalar_one() < 2:
            quots = [
                (maria, "COT-DEMO-001", 5100000, 0, 5100000, "sent"),
                (carlos, "COT-DEMO-002", 13000000, 0, 13000000, "approved"),
            ]
            for pid, num, sub, tax, total, status in quots:
                if not await _row_exists(
                    db,
                    "SELECT id FROM quotations WHERE quotation_number = :n",
                    {"n": num},
                ):
                    row = await db.execute(
                        text(
                            """INSERT INTO quotations
                               (id, quotation_number, patient_id, created_by,
                                subtotal, tax, total, valid_until, status,
                                is_active, created_at, updated_at)
                               VALUES (gen_random_uuid(), :num, :pid, :uid,
                               :sub, :tax, :total, CURRENT_DATE + interval '30 days',
                               :status, true, now() - interval '14 days', now())
                               RETURNING id"""
                        ),
                        {"num": num, "pid": pid, "uid": doctor_id,
                         "sub": sub, "tax": tax, "total": total, "status": status},
                    )
                    quot_ids[num] = str(row.mappings().first()["id"])
            await _commit(db)
            w["quotations"] = quot_ids
            _print_ok(f"Quotations: {len(quot_ids)}")

    # -- prescriptions (2) --
    if await _table_exists(db, "prescriptions"):
        existing = await db.execute(text("SELECT count(*) FROM prescriptions"))
        if existing.scalar_one() < 2:
            rxs = [
                (maria, '[{"nombre": "Ibuprofeno 400mg", "dosis": "1 cada 8 horas", "duracion": "5 días", "via": "oral"},'
                        '{"nombre": "Amoxicilina 500mg", "dosis": "1 cada 8 horas", "duracion": "7 días", "via": "oral"}]'),
                (carlos, '[{"nombre": "Acetaminofén 500mg", "dosis": "1 cada 6 horas", "duracion": "3 días", "via": "oral"}]'),
            ]
            for pid, meds in rxs:
                await db.execute(
                    text(
                        """INSERT INTO prescriptions
                           (id, patient_id, doctor_id, medications, is_active, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :doc, CAST(:meds AS jsonb), true,
                           now() - interval '7 days', now())"""
                    ),
                    {"pid": pid, "doc": doctor_id, "meds": meds},
                )
            await _commit(db)
            _print_ok("Prescriptions: 2")

    # -- intake_submissions (3) --
    intake_tmpl = w2.get("intake_template_id")
    if await _table_exists(db, "intake_submissions") and intake_tmpl:
        existing = await db.execute(text("SELECT count(*) FROM intake_submissions"))
        if existing.scalar_one() < 2:
            subs = [
                (maria, "reviewed", '{"motivo_consulta": "Control periódico y limpieza", "alergias": "Penicilina", "medicamentos": "Ibuprofeno"}'),
                (carlos, "approved", '{"motivo_consulta": "Dolor en muela", "alergias": "Ninguna", "medicamentos": "Losartán, Metformina"}'),
                (sofia, "pending", '{"motivo_consulta": "Se me rompió un diente", "alergias": "Látex", "medicamentos": "Ninguno"}'),
            ]
            for pid, status, data in subs:
                await db.execute(
                    text(
                        """INSERT INTO intake_submissions
                           (id, template_id, patient_id, data, status,
                            submitted_at, is_active, created_at, updated_at)
                           VALUES (gen_random_uuid(), :tmpl, :pid, CAST(:data AS jsonb), :status,
                           now() - interval '1 day', true, now(), now())"""
                    ),
                    {"tmpl": intake_tmpl, "pid": pid, "status": status, "data": data},
                )
            await _commit(db)
            _print_ok("Intake submissions: 3")

    # -- whatsapp_messages (15 across 3 conversations) --
    wa_convos = w3.get("whatsapp_conversations", {})
    if await _table_exists(db, "whatsapp_messages") and wa_convos:
        existing = await db.execute(text("SELECT count(*) FROM whatsapp_messages"))
        if existing.scalar_one() < 5:
            messages = [
                # María conversation
                ("+5716234567", "inbound", "Hola, buenos días. Quiero confirmar mi cita de mañana.", "delivered", None, -120),
                ("+5716234567", "outbound", "¡Hola María! Sí, su cita está confirmada para mañana a las 9:00 AM con el Dr. Ramírez.", "delivered", receptionist_id, -118),
                ("+5716234567", "inbound", "Perfecto, muchas gracias. ¿Debo llevar algo?", "delivered", None, -100),
                ("+5716234567", "outbound", "Solo su documento de identidad. Si tiene radiografías recientes, por favor tráigalas también.", "delivered", receptionist_id, -98),
                ("+5716234567", "inbound", "Listo, allá estaré. Gracias!", "read", None, -90),
                # Carlos conversation
                ("+5716891234", "inbound", "Doctor, tengo una pregunta sobre mi tratamiento.", "delivered", None, -60),
                ("+5716891234", "outbound", "Hola Carlos, dígame en qué puedo ayudarle.", "delivered", doctor_id, -55),
                ("+5716891234", "inbound", "¿Es normal sentir sensibilidad después de la corona?", "delivered", None, -50),
                ("+5716891234", "outbound", "Sí, es completamente normal. Debería desaparecer en 1-2 semanas. Si persiste, agéndese una cita de control.", "delivered", doctor_id, -45),
                ("+5716891234", "inbound", "Gracias doctor, estaré pendiente.", "read", None, -40),
                # Sofía conversation (archived)
                ("+5716452890", "inbound", "Buenas tardes, quisiera agendar una cita.", "delivered", None, -180),
                ("+5716452890", "outbound", "¡Hola Sofía! Claro, tenemos disponibilidad esta semana. ¿Qué día le conviene?", "delivered", receptionist_id, -175),
                ("+5716452890", "inbound", "El viernes en la tarde si es posible.", "delivered", None, -170),
                ("+5716452890", "outbound", "Listo, le agendé para el viernes a las 2:00 PM. ¿Le parece bien?", "delivered", receptionist_id, -165),
                ("+5716452890", "inbound", "Perfecto, gracias!", "read", None, -160),
            ]
            for phone, direction, content, status, sent_by, mins_ago in messages:
                conv_id = wa_convos.get(phone)
                if conv_id:
                    await db.execute(
                        text(
                            """INSERT INTO whatsapp_messages
                               (id, conversation_id, direction, content, status, sent_by,
                                created_at, updated_at)
                               VALUES (gen_random_uuid(), :cid, :dir, :content, :status, :sent,
                               now() + :mins * interval '1 minute', now())"""
                        ),
                        {"cid": conv_id, "dir": direction, "content": content,
                         "status": status, "sent": sent_by, "mins": mins_ago},
                    )
            await _commit(db)
            _print_ok("WhatsApp messages: 15")

    # -- nps_survey_responses (5) --
    if await _table_exists(db, "nps_survey_responses"):
        existing = await db.execute(text("SELECT count(*) FROM nps_survey_responses"))
        if existing.scalar_one() < 3:
            surveys = [
                (maria, 10, 5, "Excelente atención, muy profesional", "tok_maria_01"),
                (carlos, 8, 4, "Buen servicio, pero tuve que esperar un poco", "tok_carlos_01"),
                (sofia, 9, 5, "Me gustó mucho la clínica, muy moderna", "tok_sofia_01"),
                (luis, 3, 2, "El tiempo de espera fue excesivo", "tok_luis_01"),
                (isabela, 7, 4, None, "tok_isabela_01"),
            ]
            for pid, nps, csat, comment, token in surveys:
                if not await _row_exists(
                    db,
                    "SELECT id FROM nps_survey_responses WHERE survey_token = :t",
                    {"t": token},
                ):
                    await db.execute(
                        text(
                            """INSERT INTO nps_survey_responses
                               (id, patient_id, doctor_id, nps_score, csat_score, comments,
                                channel_sent, survey_token, responded_at, created_at, updated_at)
                               VALUES (gen_random_uuid(), :pid, :doc, :nps, :csat, :comment,
                               'whatsapp', :token, now() - (random() * interval '30 days'),
                               now(), now())"""
                        ),
                        {"pid": pid, "doc": doctor_id, "nps": nps, "csat": csat,
                         "comment": comment, "token": token},
                    )
            await _commit(db)
            _print_ok("NPS survey responses: 5")

    # -- chatbot_conversations + chatbot_messages --
    if await _table_exists(db, "chatbot_conversations"):
        existing = await db.execute(text("SELECT count(*) FROM chatbot_conversations"))
        if existing.scalar_one() < 2:
            # Web chatbot
            row = await db.execute(
                text(
                    """INSERT INTO chatbot_conversations
                       (id, channel, patient_id, status, intent_history,
                        started_at, created_at, updated_at)
                       VALUES (gen_random_uuid(), 'web', :pid, 'resolved',
                       '["schedule", "hours"]'::jsonb,
                       now() - interval '2 hours', now(), now())
                       RETURNING id"""
                ),
                {"pid": isabela},
            )
            chat1 = str(row.mappings().first()["id"])

            # WhatsApp chatbot
            row = await db.execute(
                text(
                    """INSERT INTO chatbot_conversations
                       (id, channel, patient_id, status, intent_history,
                        started_at, created_at, updated_at)
                       VALUES (gen_random_uuid(), 'whatsapp', :pid, 'active',
                       '["faq", "payment"]'::jsonb,
                       now() - interval '30 minutes', now(), now())
                       RETURNING id"""
                ),
                {"pid": luis},
            )
            chat2 = str(row.mappings().first()["id"])

            # Chatbot messages
            if await _table_exists(db, "chatbot_messages"):
                chat_msgs = [
                    (chat1, "user", "Hola, quiero agendar una cita", "schedule", 0.92),
                    (chat1, "assistant", "¡Hola! Con gusto le ayudo a agendar su cita. ¿Para qué tipo de consulta necesita cita?", None, None),
                    (chat1, "user", "Consulta general. ¿Qué horarios tienen?", "hours", 0.85),
                    (chat1, "assistant", "Atendemos de lunes a viernes de 8:00 AM a 6:00 PM y sábados de 8:00 AM a 1:00 PM. ¿Qué día le conviene?", None, None),
                    (chat1, "user", "El martes a las 10 AM", "schedule", 0.95),
                    (chat1, "assistant", "Perfecto, le he agendado una consulta general para el martes a las 10:00 AM. ¿Necesita algo más?", None, None),
                    (chat2, "user", "¿Cuánto cuesta una limpieza dental?", "faq", 0.88),
                    (chat2, "assistant", "La profilaxis dental (limpieza) tiene un costo de $150,000 COP. ¿Le gustaría agendar una cita?", None, None),
                ]
                for cid, role, content, intent, conf in chat_msgs:
                    await db.execute(
                        text(
                            """INSERT INTO chatbot_messages
                               (id, conversation_id, role, content, intent, confidence_score, created_at)
                               VALUES (gen_random_uuid(), :cid, :role, :content, :intent, :conf, now())"""
                        ),
                        {"cid": cid, "role": role, "content": content,
                         "intent": intent, "conf": conf},
                    )
            await _commit(db)
            _print_ok("Chatbot: 2 conversations, 8 messages")

    # -- email_campaigns (1 + 5 recipients) --
    if await _table_exists(db, "email_campaigns") and owner_id:
        existing = await db.execute(text("SELECT count(*) FROM email_campaigns"))
        if existing.scalar_one() < 1:
            row = await db.execute(
                text(
                    """INSERT INTO email_campaigns
                       (id, name, subject, template_id, segment_filters, status,
                        sent_at, sent_count, open_count, click_count, created_by,
                        is_active, created_at, updated_at)
                       VALUES (gen_random_uuid(), 'Campaña Mes de la Salud Oral',
                       '¡Cuide su sonrisa! 20% de descuento en profilaxis este mes',
                       'health_month_2026', '{}'::jsonb, 'sent',
                       now() - interval '3 days', 5, 3, 1, :uid,
                       true, now(), now())
                       RETURNING id"""
                ),
                {"uid": owner_id},
            )
            campaign_id = str(row.mappings().first()["id"])

            if await _table_exists(db, "email_campaign_recipients"):
                patients_emails = [
                    (maria, "maria.gonzalez@gmail.com", "opened"),
                    (carlos, "carlos.martinez@hotmail.com", "clicked"),
                    (sofia, "sofia.hernandez@outlook.com", "opened"),
                    (luis, "luis.jimenez@gmail.com", "sent"),
                    (isabela, "isabela.sanchez@gmail.com", "bounced"),
                ]
                for pid, email, status in patients_emails:
                    opened_expr = "now() - interval '2 days'" if status in ("opened", "clicked") else "NULL"
                    clicked_expr = "now() - interval '1 day'" if status == "clicked" else "NULL"
                    await db.execute(
                        text(
                            f"""INSERT INTO email_campaign_recipients
                               (id, campaign_id, patient_id, email, status,
                                sent_at, opened_at, clicked_at, created_at, updated_at)
                               VALUES (gen_random_uuid(), :cid, :pid, :email, :status,
                               now() - interval '3 days',
                               {opened_expr},
                               {clicked_expr},
                               now(), now())"""
                        ),
                        {"cid": campaign_id, "pid": pid, "email": email, "status": status},
                    )
            await _commit(db)
            _print_ok("Email campaign: 1 + 5 recipients")

    return w


# ---------------------------------------------------------------------------
# Wave 6: Invoices, billing, satisfaction
# ---------------------------------------------------------------------------


async def wave_6_invoices(db: AsyncSession, ids: dict, w5: dict) -> dict:
    """Insert invoices, invoice_items, quotation_items, satisfaction_surveys, video_sessions."""
    _print_section("Wave 6: Invoices & billing")
    w = {}
    doctor_id = ids["users"].get("doctor")
    receptionist_id = ids["users"].get("receptionist")
    maria = ids["patients"].get("maria")
    carlos = ids["patients"].get("carlos")
    sofia = ids["patients"].get("sofia")
    luis = ids["patients"].get("luis")
    isabela = ids["patients"].get("isabela")

    if not doctor_id or not maria:
        _print_skip("Missing IDs")
        return w

    # -- invoices (5 in different states) --
    inv_ids = {}
    if await _table_exists(db, "invoices"):
        # Resolve any existing demo invoices first
        for demo_num in ["DEMO-001", "DEMO-002", "DEMO-003", "DEMO-004", "DEMO-005"]:
            row = await db.execute(
                text("SELECT id FROM invoices WHERE invoice_number = :n"), {"n": demo_num}
            )
            eid = row.scalar_one_or_none()
            if eid:
                inv_ids[demo_num] = str(eid)

        existing = await db.execute(text("SELECT count(*) FROM invoices"))
        if existing.scalar_one() < 3:
            invoices = [
                ("DEMO-001", maria, 1500000, 0, 1500000, 1500000, 0, "paid"),
                ("DEMO-002", carlos, 13000000, 0, 13000000, 8000000, 5000000, "partial"),
                ("DEMO-003", sofia, 1800000, 0, 1800000, 0, 1800000, "overdue"),
                ("DEMO-004", luis, 800000, 0, 800000, 0, 800000, "sent"),
                ("DEMO-005", isabela, 5000000, 0, 5000000, 0, 5000000, "draft"),
            ]
            for num, pid, sub, tax, total, paid, balance, status in invoices:
                if not await _row_exists(
                    db,
                    "SELECT id FROM invoices WHERE invoice_number = :n",
                    {"n": num},
                ):
                    due_expr = "CURRENT_DATE + interval '30 days'"
                    if status == "overdue":
                        due_expr = "CURRENT_DATE - interval '15 days'"
                    elif status == "paid":
                        due_expr = "CURRENT_DATE - interval '5 days'"

                    paid_at_expr = "now() - interval '3 days'" if status == "paid" else "NULL"
                    row = await db.execute(
                        text(
                            f"""INSERT INTO invoices
                               (id, invoice_number, patient_id, created_by,
                                subtotal, tax, total, amount_paid, balance,
                                status, due_date,
                                paid_at, currency_code,
                                is_active, created_at, updated_at)
                               VALUES (gen_random_uuid(), :num, :pid, :uid,
                               :sub, :tax, :total, :paid, :balance,
                               :status, {due_expr},
                               {paid_at_expr},
                               'COP', true,
                               now() - interval '14 days', now())
                               RETURNING id"""
                        ),
                        {"num": num, "pid": pid, "uid": receptionist_id,
                         "sub": sub, "tax": tax, "total": total, "paid": paid,
                         "balance": balance, "status": status},
                    )
                    inv_ids[num] = str(row.mappings().first()["id"])
            await _commit(db)
            _print_ok(f"Invoices: {len(inv_ids)} (new inserts)")
        else:
            _print_skip(f"Invoices already exist, resolved {len(inv_ids)} IDs")

        w["invoices"] = inv_ids

    # -- invoice_items --
    if await _table_exists(db, "invoice_items") and inv_ids:
        items_data = [
            ("DEMO-001", "Profilaxis dental", "997120", 1, 1500000, 0),
            ("DEMO-002", "Endodoncia unirradicular", "997410", 1, 4500000, 0),
            ("DEMO-002", "Corona cerámica", "997610", 1, 8500000, 0),
            ("DEMO-003", "Resina compuesta", "997310", 1, 1800000, 0),
            ("DEMO-004", "Consulta odontológica general", "990201", 1, 800000, 0),
            ("DEMO-005", "Blanqueamiento dental", "997810", 1, 5000000, 0),
        ]
        for inv_num, desc, cups, qty, price, discount in items_data:
            inv_id = inv_ids.get(inv_num)
            if inv_id:
                existing = await db.execute(
                    text("SELECT count(*) FROM invoice_items WHERE invoice_id = :iid"),
                    {"iid": inv_id},
                )
                if existing.scalar_one() == 0:
                    line_total = price * qty - discount
                    await db.execute(
                        text(
                            """INSERT INTO invoice_items
                               (id, invoice_id, description, cups_code, quantity,
                                unit_price, discount, line_total, sort_order, created_at, updated_at)
                               VALUES (gen_random_uuid(), :iid, :desc, :cups, :qty,
                               :price, :disc, :ltotal, 1, now(), now())"""
                        ),
                        {"iid": inv_id, "desc": desc, "cups": cups, "qty": qty,
                         "price": price, "disc": discount, "ltotal": line_total},
                    )
        await _commit(db)
        _print_ok("Invoice items: 6")

    # -- quotation_items --
    quot_ids = w5.get("quotations", {})
    # Resolve existing quotation IDs if not in wave dict
    if not quot_ids and await _table_exists(db, "quotations"):
        for qnum in ["COT-DEMO-001", "COT-DEMO-002"]:
            row = await db.execute(
                text("SELECT id FROM quotations WHERE quotation_number = :n"), {"n": qnum}
            )
            eid = row.scalar_one_or_none()
            if eid:
                quot_ids[qnum] = str(eid)
    if await _table_exists(db, "quotation_items") and quot_ids:
        q_items = [
            ("COT-DEMO-001", "Profilaxis dental", "997120", 1, 1500000, 0, 1),
            ("COT-DEMO-001", "Resina compuesta 36 mesial", "997310", 1, 1800000, 0, 2),
            ("COT-DEMO-001", "Resina compuesta 36 oclusal", "997310", 1, 1800000, 0, 3),
            ("COT-DEMO-002", "Endodoncia unirradicular", "997410", 1, 4500000, 0, 1),
            ("COT-DEMO-002", "Corona cerámica", "997610", 1, 8500000, 0, 2),
        ]
        for qnum, desc, cups, qty, price, disc, order in q_items:
            qid = quot_ids.get(qnum)
            if qid:
                existing = await db.execute(
                    text("SELECT count(*) FROM quotation_items WHERE quotation_id = :qid"),
                    {"qid": qid},
                )
                if existing.scalar_one() == 0:
                    line_total = price * qty - disc
                    await db.execute(
                        text(
                            """INSERT INTO quotation_items
                               (id, quotation_id, description, cups_code, quantity,
                                unit_price, discount, line_total, sort_order, created_at, updated_at)
                               VALUES (gen_random_uuid(), :qid, :desc, :cups, :qty,
                               :price, :disc, :ltotal, :ord, now(), now())"""
                        ),
                        {"qid": qid, "desc": desc, "cups": cups, "qty": qty,
                         "price": price, "disc": disc, "ltotal": line_total, "ord": order},
                    )
        await _commit(db)
        _print_ok("Quotation items: 5")

    # -- satisfaction_surveys (3) --
    if await _table_exists(db, "satisfaction_surveys"):
        existing = await db.execute(text("SELECT count(*) FROM satisfaction_surveys"))
        if existing.scalar_one() < 2:
            for pid, score, feedback, token, routed in [
                (maria, 5, "Todo excelente, muy profesional", "sat_maria_01", "google_review"),
                (carlos, 4, "Buen servicio pero la espera fue larga", "sat_carlos_01", "private_feedback"),
                (sofia, 5, None, "sat_sofia_01", "google_review"),
            ]:
                if not await _row_exists(
                    db,
                    "SELECT id FROM satisfaction_surveys WHERE survey_token = :t",
                    {"t": token},
                ):
                    await db.execute(
                        text(
                            """INSERT INTO satisfaction_surveys
                               (id, patient_id, score, feedback_text, channel_sent,
                                survey_token, routed_to, sent_at, responded_at, created_at, updated_at)
                               VALUES (gen_random_uuid(), :pid, :score, :fb, 'whatsapp',
                               :token, :routed,
                               now() - interval '5 days', now() - interval '4 days', now(), now())"""
                        ),
                        {"pid": pid, "score": score, "fb": feedback,
                         "token": token, "routed": routed},
                    )
            await _commit(db)
            _print_ok("Satisfaction surveys: 3")

    # -- video_sessions (1) --
    if await _table_exists(db, "video_sessions") and await _table_exists(db, "appointments"):
        existing = await db.execute(text("SELECT count(*) FROM video_sessions"))
        if existing.scalar_one() < 1:
            # Pick a future scheduled appointment for the video session
            row = await db.execute(
                text(
                    "SELECT id FROM appointments WHERE status = 'scheduled' "
                    "AND start_time > CURRENT_TIMESTAMP ORDER BY start_time LIMIT 1"
                )
            )
            future_appt = row.scalar_one_or_none()
            if future_appt:
                await db.execute(
                    text(
                        """INSERT INTO video_sessions
                           (id, appointment_id, provider, status,
                            join_url_doctor, join_url_patient, created_at, updated_at)
                           VALUES (gen_random_uuid(), :aid, 'daily', 'created',
                           'https://dentalos.daily.co/room-demo-001?t=doctor_token',
                           'https://dentalos.daily.co/room-demo-001?t=patient_token',
                           now(), now())"""
                    ),
                    {"aid": str(future_appt)},
                )
                await _commit(db)
                _print_ok("Video session: 1")

    return w


# ---------------------------------------------------------------------------
# Wave 7: Payments + financing
# ---------------------------------------------------------------------------


async def wave_7_payments(db: AsyncSession, ids: dict, w6: dict) -> dict:
    """Insert payments, financing_applications, referral_rewards."""
    _print_section("Wave 7: Payments & financing")
    w = {}
    receptionist_id = ids["users"].get("receptionist")
    maria = ids["patients"].get("maria")
    carlos = ids["patients"].get("carlos")
    sofia = ids["patients"].get("sofia")
    isabela = ids["patients"].get("isabela")
    inv_ids = w6.get("invoices", {})

    # -- payments (3) --
    pay_ids = {}
    if await _table_exists(db, "payments") and inv_ids:
        # Payment for DEMO-001 (paid in full)
        inv1 = inv_ids.get("DEMO-001")
        inv2 = inv_ids.get("DEMO-002")
        if inv1 and not await _row_exists(
            db, "SELECT id FROM payments WHERE invoice_id = :i", {"i": inv1}
        ):
            row = await db.execute(
                text(
                    """INSERT INTO payments
                       (id, invoice_id, patient_id, amount, payment_method,
                        reference_number, received_by, payment_date, created_at, updated_at)
                       VALUES (gen_random_uuid(), :iid, :pid, 1500000, 'nequi',
                       'NEQ-2026-001', :uid, now() - interval '3 days', now(), now())
                       RETURNING id"""
                ),
                {"iid": inv1, "pid": maria, "uid": receptionist_id},
            )
            pay_ids["pay_1"] = str(row.mappings().first()["id"])

        # Payment for DEMO-002 (partial: 8M of 13M)
        if inv2 and not await _row_exists(
            db, "SELECT id FROM payments WHERE invoice_id = :i", {"i": inv2}
        ):
            row = await db.execute(
                text(
                    """INSERT INTO payments
                       (id, invoice_id, patient_id, amount, payment_method,
                        reference_number, received_by, payment_date, created_at, updated_at)
                       VALUES (gen_random_uuid(), :iid, :pid, 8000000, 'card',
                       'CARD-2026-002', :uid, now() - interval '7 days', now(), now())
                       RETURNING id"""
                ),
                {"iid": inv2, "pid": carlos, "uid": receptionist_id},
            )
            pay_ids["pay_2"] = str(row.mappings().first()["id"])

        await _commit(db)
        w["payments"] = pay_ids
        _print_ok(f"Payments: {len(pay_ids)}")

    # -- financing_applications (2) --
    fin_ids = {}
    if await _table_exists(db, "financing_applications"):
        existing = await db.execute(text("SELECT count(*) FROM financing_applications"))
        if existing.scalar_one() < 2:
            inv3 = inv_ids.get("DEMO-003")
            inv5 = inv_ids.get("DEMO-005")
            apps = [
                (sofia, inv3, "addi", "approved", 1800000, 3, 250, "ADDI-REF-001"),
                (isabela, inv5, "sistecredito", "requested", 5000000, 6, None, None),
            ]
            for pid, iid, provider, status, amount, installments, rate, ref in apps:
                approved_expr = "now() - interval '1 day'" if status == "approved" else "NULL"
                row = await db.execute(
                    text(
                        f"""INSERT INTO financing_applications
                           (id, patient_id, invoice_id, provider, status, amount_cents,
                            installments, interest_rate_bps, provider_reference,
                            approved_at, created_at, updated_at)
                           VALUES (gen_random_uuid(), :pid, :iid, :prov, :status, :amount,
                           :inst, :rate, :ref,
                           {approved_expr},
                           now(), now())
                           RETURNING id"""
                    ),
                    {"pid": pid, "iid": iid, "prov": provider, "status": status,
                     "amount": amount, "inst": installments, "rate": rate, "ref": ref},
                )
                fin_ids[provider] = str(row.mappings().first()["id"])
            await _commit(db)
            w["financing"] = fin_ids
            _print_ok(f"Financing applications: {len(fin_ids)}")

    # -- referral_rewards (1) --
    ref_codes = {}
    if await _table_exists(db, "referral_codes"):
        row = await db.execute(
            text("SELECT id FROM referral_codes WHERE code = 'MARIA25'")
        )
        r = row.scalar_one_or_none()
        if r:
            ref_codes["MARIA25"] = str(r)

    if await _table_exists(db, "referral_rewards") and ref_codes.get("MARIA25") and maria and isabela:
        if not await _row_exists(
            db,
            "SELECT id FROM referral_rewards WHERE referrer_patient_id = :r AND referred_patient_id = :d",
            {"r": maria, "d": isabela},
        ):
            await db.execute(
                text(
                    """INSERT INTO referral_rewards
                       (id, referrer_patient_id, referred_patient_id, referral_code_id,
                        reward_type, reward_amount_cents, status, created_at, updated_at)
                       VALUES (gen_random_uuid(), :referrer, :referred, :code_id,
                       'discount', 5000000, 'pending', now(), now())"""
                ),
                {"referrer": maria, "referred": isabela,
                 "code_id": ref_codes["MARIA25"]},
            )
            await _commit(db)
            _print_ok("Referral reward: 1")

    return w


# ---------------------------------------------------------------------------
# Wave 8: Payment plans
# ---------------------------------------------------------------------------


async def wave_8_payment_plans(db: AsyncSession, ids: dict, w6: dict) -> dict:
    """Insert payment_plans and payment_plan_installments."""
    _print_section("Wave 8: Payment plans")
    w = {}
    receptionist_id = ids["users"].get("receptionist")
    carlos = ids["patients"].get("carlos")
    inv_ids = w6.get("invoices", {})
    inv2 = inv_ids.get("DEMO-002")

    if not await _table_exists(db, "payment_plans") or not inv2:
        _print_skip("payment_plans table or invoice not available")
        return w

    if await _row_exists(
        db, "SELECT id FROM payment_plans WHERE invoice_id = :i", {"i": inv2}
    ):
        _print_skip("Payment plan already exists")
        return w

    row = await db.execute(
        text(
            """INSERT INTO payment_plans
               (id, invoice_id, patient_id, total_amount, num_installments,
                status, created_by, is_active, created_at, updated_at)
               VALUES (gen_random_uuid(), :iid, :pid, 5000000, 3,
               'active', :uid, true, now(), now())
               RETURNING id"""
        ),
        {"iid": inv2, "pid": carlos, "uid": receptionist_id},
    )
    plan_id = str(row.mappings().first()["id"])
    w["payment_plan_id"] = plan_id

    # 3 installments
    if await _table_exists(db, "payment_plan_installments"):
        installments = [
            (1, 1700000, -5, "paid"),
            (2, 1700000, 25, "pending"),
            (3, 1600000, 55, "pending"),
        ]
        for num, amount, days, status in installments:
            paid_at_expr = "now() - interval '3 days'" if status == "paid" else "NULL"
            await db.execute(
                text(
                    f"""INSERT INTO payment_plan_installments
                       (id, plan_id, installment_number, amount, due_date,
                        status, paid_at, created_at, updated_at)
                       VALUES (gen_random_uuid(), :pid, :num, :amount,
                       CURRENT_DATE + :days * interval '1 day',
                       :status,
                       {paid_at_expr},
                       now(), now())"""
                ),
                {"pid": plan_id, "num": num, "amount": amount,
                 "days": days, "status": status},
            )
    await _commit(db)
    _print_ok("Payment plan: 1 + 3 installments")
    return w


# ---------------------------------------------------------------------------
# Wave 9: Financing payments
# ---------------------------------------------------------------------------


async def wave_9_financing_payments(db: AsyncSession, w7: dict) -> dict:
    """Insert financing_payments for approved application."""
    _print_section("Wave 9: Financing installments")
    w = {}
    fin_ids = w7.get("financing", {})
    addi_id = fin_ids.get("addi")

    if not await _table_exists(db, "financing_payments") or not addi_id:
        _print_skip("financing_payments table or application not available")
        return w

    existing = await db.execute(
        text("SELECT count(*) FROM financing_payments WHERE application_id = :a"),
        {"a": addi_id},
    )
    if existing.scalar_one() > 0:
        _print_skip("Financing payments already exist")
        return w

    installments = [
        (1, 600000, -10, "paid"),
        (2, 600000, 20, "pending"),
        (3, 600000, 50, "pending"),
    ]
    for num, amount, days, status in installments:
        paid_at_expr = "now() - interval '5 days'" if status == "paid" else "NULL"
        await db.execute(
            text(
                f"""INSERT INTO financing_payments
                   (id, application_id, installment_number, amount_cents,
                    due_date, status,
                    paid_at, created_at, updated_at)
                   VALUES (gen_random_uuid(), :aid, :num, :amount,
                   CURRENT_DATE + :days * interval '1 day',
                   :status,
                   {paid_at_expr},
                   now(), now())"""
            ),
            {"aid": addi_id, "num": num, "amount": amount,
             "days": days, "status": status},
        )
    await _commit(db)
    _print_ok("Financing payments: 3")
    return w


# ---------------------------------------------------------------------------
# Cash movements (depends on wave 2 cash register + wave 6 invoices)
# ---------------------------------------------------------------------------


async def wave_extra_cash_movements(db: AsyncSession, ids: dict, w2: dict, w6: dict) -> None:
    """Insert cash_movements tied to the open register."""
    _print_section("Extra: Cash register movements")
    register_id = w2.get("cash_register_id")
    receptionist_id = ids["users"].get("receptionist")

    if not await _table_exists(db, "cash_movements") or not register_id:
        _print_skip("cash_movements or register not available")
        return

    existing = await db.execute(
        text("SELECT count(*) FROM cash_movements WHERE register_id = :r"),
        {"r": register_id},
    )
    if existing.scalar_one() > 3:
        _print_skip("Cash movements already exist")
        return

    movements = [
        ("income", 1500000, "cash", "Pago consulta María González"),
        ("income", 8000000, "card", "Pago parcial Carlos Martínez"),
        ("income", 500000, "nequi", "Copago EPS Sofía Hernández"),
        ("expense", 35000000, "transfer", "Compra insumos dentales"),
        ("income", 800000, "daviplata", "Pago consulta Luis Jiménez"),
        ("income", 1200000, "cash", "Pago radiografía periapical"),
        ("expense", 8500000, "transfer", "Pago laboratorio dental"),
        ("adjustment", -200000, None, "Ajuste por error en cobro"),
    ]
    for mtype, amount, method, desc in movements:
        await db.execute(
            text(
                """INSERT INTO cash_movements
                   (id, register_id, type, amount_cents, payment_method,
                    description, recorded_by, created_at, updated_at)
                   VALUES (gen_random_uuid(), :rid, :type, :amount, :method,
                   :desc, :uid, now() - (random() * interval '8 hours'), now())"""
            ),
            {"rid": register_id, "type": mtype, "amount": amount,
             "method": method, "desc": desc, "uid": receptionist_id},
        )
    await _commit(db)
    _print_ok("Cash movements: 8")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def main() -> None:
    print("\nDentalOS — Comprehensive Demo Data Seeder")
    print("------------------------------------------")

    async with AsyncSessionLocal() as db:
        # Set search_path to the demo tenant schema
        await db.execute(text(f"SET search_path TO {DEMO_SCHEMA}, public"))

        # Wave 0: Resolve existing IDs
        ids = await wave_0_resolve_ids(db)

        if not ids["users"].get("doctor") or not ids["patients"].get("maria"):
            print("\n  [ERROR] Required users/patients not found.")
            print("  Run seed_dev.py first: python scripts/seed_dev.py")
            return

        # Each wave is wrapped in try/except so a failure in one wave
        # doesn't block all subsequent waves.  After an exception the
        # session is rolled back to keep it usable.
        w1: dict = {}
        w2: dict = {}
        w3: dict = {}
        w4: dict = {}
        w5: dict = {}
        w6: dict = {}
        w7: dict = {}
        w8: dict = {}
        w9: dict = {}

        for label, fn in [
            ("Wave 1", lambda: wave_1_config(db, ids)),
            ("Wave 2", lambda: wave_2_user_config(db, ids)),
        ]:
            try:
                result = await fn()
                if label == "Wave 1":
                    w1 = result
                elif label == "Wave 2":
                    w2 = result
            except Exception as exc:
                await _rollback(db)
                print(f"  [ERR] {label} failed: {exc}")

        try:
            w3 = await wave_3_clinical(db, ids, w1)
        except Exception as exc:
            await _rollback(db)
            print(f"  [ERR] Wave 3 failed: {exc}")

        try:
            w4 = await wave_4_tp_items(db, ids, w1, w3)
        except Exception as exc:
            await _rollback(db)
            print(f"  [ERR] Wave 4 failed: {exc}")

        try:
            w5 = await wave_5_appointments(db, ids, w1, w2, w3)
        except Exception as exc:
            await _rollback(db)
            print(f"  [ERR] Wave 5 failed: {exc}")

        try:
            w6 = await wave_6_invoices(db, ids, w5)
        except Exception as exc:
            await _rollback(db)
            print(f"  [ERR] Wave 6 failed: {exc}")

        try:
            w7 = await wave_7_payments(db, ids, w6)
        except Exception as exc:
            await _rollback(db)
            print(f"  [ERR] Wave 7 failed: {exc}")

        try:
            w8 = await wave_8_payment_plans(db, ids, w6)
        except Exception as exc:
            await _rollback(db)
            print(f"  [ERR] Wave 8 failed: {exc}")

        try:
            w9 = await wave_9_financing_payments(db, w7)
        except Exception as exc:
            await _rollback(db)
            print(f"  [ERR] Wave 9 failed: {exc}")

        try:
            await wave_extra_cash_movements(db, ids, w2, w6)
        except Exception as exc:
            await _rollback(db)
            print(f"  [ERR] Wave Extra failed: {exc}")

    _print_section("Demo Data Seeding Complete!")
    print("  All modules should now have realistic data.")
    print("  Login as owner@demo.dentalos.co / DemoPass1")
    print("  Flush Redis cache: docker exec dentalos-redis redis-cli FLUSHDB")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
