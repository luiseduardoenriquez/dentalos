# Testing Infrastructure Spec

## Overview

**Feature:** Complete testing infrastructure for DentalOS backend (FastAPI/Python) and frontend (Next.js/React), including test framework configuration, factory patterns, fixtures, mocking strategies, CI/CD pipeline, and coverage enforcement.

**Domain:** infra

**Priority:** Critical

**Dependencies:** None (foundational spec; other specs reference this for test conventions)

**Spec ID:** I-08

---

## 1. Backend Testing Framework

### 1.1 Core Stack

| Tool | Version | Purpose |
|------|---------|---------|
| pytest | >= 8.0 | Test framework and runner |
| pytest-asyncio | >= 0.23 | Async test support for FastAPI endpoints |
| httpx | >= 0.27 | AsyncClient for FastAPI TestClient replacement |
| factory_boy | >= 3.3 | Test data factories |
| faker | >= 24.0 | Realistic fake data generation (locale: `es_CO`) |
| pytest-cov | >= 5.0 | Coverage reporting |
| pytest-xdist | >= 3.5 | Parallel test execution |
| pytest-env | >= 1.1 | Environment variable management for tests |
| respx | >= 0.21 | Mocking httpx requests (external API calls) |
| freezegun | >= 1.4 | Time freezing for date-dependent tests |
| moto | >= 5.0 | AWS S3 / MinIO mock (boto3 compatible) |

### 1.2 Directory Structure

```
backend/
  tests/
    conftest.py                    # Global fixtures (db session, tenant, auth)
    factories/
      __init__.py
      tenant_factory.py            # TenantFactory, PlanFactory
      user_factory.py              # UserFactory (parameterized by role)
      patient_factory.py           # PatientFactory, EmergencyContactFactory
      odontogram_factory.py        # OdontogramConditionFactory, ToothFactory
      clinical_record_factory.py   # ClinicalRecordFactory, DiagnosisFactory, ProcedureFactory
      appointment_factory.py       # AppointmentFactory, AvailabilityBlockFactory
      billing_factory.py           # InvoiceFactory, PaymentFactory, LineItemFactory
      treatment_plan_factory.py    # TreatmentPlanFactory, PlanItemFactory
      consent_factory.py           # ConsentTemplateFactory, ConsentFactory
      prescription_factory.py      # PrescriptionFactory, MedicationFactory
    unit/
      test_models/                 # SQLAlchemy model unit tests
      test_services/               # Business logic service tests
      test_validators/             # Pydantic schema validation tests
      test_utils/                  # Utility function tests
    integration/
      test_api/                    # API endpoint integration tests
        test_auth/
        test_patients/
        test_odontogram/
        test_clinical_records/
        test_appointments/
        test_billing/
        test_treatment_plans/
        test_consents/
        test_prescriptions/
        test_admin/
        test_portal/
      test_db/                     # Database-level integration tests
      test_cache/                  # Redis cache integration tests
      test_queue/                  # RabbitMQ job dispatch tests
    e2e/                           # Backend E2E (full request lifecycle)
    fixtures/
      cie10_sample.json            # Subset of CIE-10 codes for tests
      cups_sample.json             # Subset of CUPS codes for tests
      seed_odontogram.json         # Sample odontogram state
```

### 1.3 pytest Configuration

**`pyproject.toml`:**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
    "--tb=short",
    "--cov=app",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-fail-under=80",
]
markers = [
    "unit: Unit tests (no DB, no network)",
    "integration: Integration tests (requires DB)",
    "e2e: End-to-end tests (full stack)",
    "slow: Tests that take > 2 seconds",
]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning",
]
env = [
    "ENVIRONMENT=test",
    "DATABASE_URL=postgresql+asyncpg://dentalos_test:test@localhost:5433/dentalos_test",
    "REDIS_URL=redis://localhost:6380/0",
    "SECRET_KEY=test-secret-key-not-for-production",
    "JWT_SECRET=test-jwt-secret-not-for-production",
]
```

---

## 2. Test Database Configuration

### 2.1 Separate Test Database

Tests run against a dedicated PostgreSQL instance (port `5433`) to avoid conflicts with the development database.

```
Host:     localhost
Port:     5433
Database: dentalos_test
User:     dentalos_test
Password: test
```

**Docker Compose service (test-only):**

```yaml
services:
  postgres-test:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: dentalos_test
      POSTGRES_USER: dentalos_test
      POSTGRES_PASSWORD: test
    ports:
      - "5433:5432"
    tmpfs:
      - /var/lib/postgresql/data  # RAM-backed for speed
    command: >
      postgres
        -c fsync=off
        -c synchronous_commit=off
        -c full_page_writes=off
        -c max_connections=200
```

**Performance note:** `tmpfs` + disabled `fsync` makes tests 3-5x faster. Data is intentionally ephemeral.

### 2.2 Schema-per-Tenant Test Isolation

Each test that requires a tenant gets a unique PostgreSQL schema, matching the production multi-tenant architecture.

**Isolation strategy:**

1. **Per-test-session:** A shared schema `test_shared` is created once with catalog data (CIE-10, CUPS, plans).
2. **Per-test-function:** Each test that needs a tenant creates a schema named `tenant_{uuid_short}`, runs its assertions, then drops the schema in teardown.
3. **Parallel safety:** `pytest-xdist` workers each get unique tenant schema names, preventing collisions.

```python
# conftest.py — Simplified schema lifecycle
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def test_tenant_schema(test_db_engine):
    """Create an isolated tenant schema for a single test."""
    schema_name = f"tenant_{uuid.uuid4().hex[:12]}"
    async with test_db_engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA {schema_name}"))
        await conn.execute(text(f"SET search_path TO {schema_name}, public"))
        # Run tenant schema migrations
        await run_tenant_migrations(conn, schema_name)
    yield schema_name
    async with test_db_engine.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA {schema_name} CASCADE"))
```

---

## 3. Factory Patterns (factory_boy)

All factories use `factory_boy` with `faker` (locale `es_CO` for realistic LATAM data). Factories produce SQLAlchemy model instances.

### 3.1 TenantFactory

```python
class PlanFactory(factory.Factory):
    class Meta:
        model = Plan

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Iterator(["free", "professional", "enterprise"])
    max_patients = factory.LazyAttribute(
        lambda o: {"free": 50, "professional": 500, "enterprise": 10000}[o.name]
    )
    max_doctors = factory.LazyAttribute(
        lambda o: {"free": 2, "professional": 10, "enterprise": 50}[o.name]
    )
    max_storage_mb = factory.LazyAttribute(
        lambda o: {"free": 500, "professional": 5000, "enterprise": 50000}[o.name]
    )
    price_usd = factory.LazyAttribute(
        lambda o: {"free": 0, "professional": 49, "enterprise": 149}[o.name]
    )


class TenantFactory(factory.Factory):
    class Meta:
        model = Tenant

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker("company", locale="es_CO")
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    country = factory.Iterator(["CO", "MX", "CL", "AR", "PE"])
    status = "active"
    plan = factory.SubFactory(PlanFactory, name="professional")
    schema_name = factory.LazyAttribute(lambda o: f"tenant_{o.id.hex[:12]}")
    odontogram_mode = "classic"
    created_at = factory.LazyFunction(datetime.utcnow)
```

### 3.2 UserFactory (Per Role)

```python
class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.LazyFunction(uuid.uuid4)
    tenant_id = factory.SelfAttribute("..tenant.id")  # Parent context
    email = factory.Faker("email", locale="es_CO")
    first_name = factory.Faker("first_name", locale="es_CO")
    last_name = factory.Faker("last_name", locale="es_CO")
    phone = factory.Faker("phone_number", locale="es_CO")
    role = "doctor"
    is_active = True
    password_hash = factory.LazyFunction(
        lambda: hash_password("TestPassword123!")
    )

    class Params:
        clinic_owner = factory.Trait(role="clinic_owner")
        doctor = factory.Trait(role="doctor")
        assistant = factory.Trait(role="assistant")
        receptionist = factory.Trait(role="receptionist")
        superadmin = factory.Trait(role="superadmin")
```

**Usage:**

```python
owner = UserFactory(clinic_owner=True)
doctor = UserFactory(doctor=True)
receptionist = UserFactory(receptionist=True)
```

### 3.3 PatientFactory

```python
class PatientFactory(factory.Factory):
    class Meta:
        model = Patient

    id = factory.LazyFunction(uuid.uuid4)
    tenant_id = factory.SelfAttribute("..tenant.id")
    first_name = factory.Faker("first_name", locale="es_CO")
    last_name = factory.Faker("last_name", locale="es_CO")
    document_type = "CC"  # Cedula de Ciudadania
    document_number = factory.Faker("numerify", text="##########")
    birthdate = factory.Faker("date_of_birth", minimum_age=5, maximum_age=90)
    gender = factory.Iterator(["M", "F", "O"])
    phone = factory.Faker("phone_number", locale="es_CO")
    email = factory.Faker("email", locale="es_CO")
    address = factory.Faker("address", locale="es_CO")
    allergies = factory.LazyFunction(lambda: [])
    medical_conditions = factory.LazyFunction(lambda: [])
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)
```

### 3.4 OdontogramConditionFactory

```python
class OdontogramConditionFactory(factory.Factory):
    class Meta:
        model = OdontogramCondition

    id = factory.LazyFunction(uuid.uuid4)
    patient_id = factory.SelfAttribute("..patient.id")
    tooth_number = factory.Iterator(range(11, 49))  # FDI notation
    zone = factory.Iterator(["mesial", "distal", "vestibular", "lingual", "oclusal", "root"])
    condition_code = factory.Iterator([
        "sano", "caries", "resina", "amalgama", "corona",
        "ausente", "implante", "endodoncia", "sellante",
        "fractura", "caries_profunda", "abrasion",
    ])
    notes = factory.Faker("sentence", locale="es_CO")
    created_by = factory.SelfAttribute("..doctor.id")
    created_at = factory.LazyFunction(datetime.utcnow)
```

### 3.5 ClinicalRecordFactory and DiagnosisFactory

```python
class ClinicalRecordFactory(factory.Factory):
    class Meta:
        model = ClinicalRecord

    id = factory.LazyFunction(uuid.uuid4)
    patient_id = factory.SelfAttribute("..patient.id")
    record_type = factory.Iterator([
        "anamnesis", "examination", "diagnosis", "evolution_note", "procedure",
    ])
    content = factory.Faker("paragraph", nb_sentences=5, locale="es_CO")
    doctor_id = factory.SelfAttribute("..doctor.id")
    appointment_id = None  # Optional link
    created_at = factory.LazyFunction(datetime.utcnow)


class DiagnosisFactory(factory.Factory):
    class Meta:
        model = Diagnosis

    id = factory.LazyFunction(uuid.uuid4)
    patient_id = factory.SelfAttribute("..patient.id")
    cie10_code = factory.Iterator(["K02.1", "K04.0", "K05.1", "K08.1", "K03.0"])
    description = factory.Iterator([
        "Caries de la dentina",
        "Pulpitis",
        "Gingivitis cronica",
        "Perdida de dientes por accidente",
        "Abrasion excesiva de los dientes",
    ])
    tooth_number = factory.LazyFunction(lambda: random.randint(11, 48))
    severity = factory.Iterator(["mild", "moderate", "severe"])
    status = "active"
    doctor_id = factory.SelfAttribute("..doctor.id")
    created_at = factory.LazyFunction(datetime.utcnow)
```

### 3.6 AppointmentFactory

```python
class AppointmentFactory(factory.Factory):
    class Meta:
        model = Appointment

    id = factory.LazyFunction(uuid.uuid4)
    patient_id = factory.SelfAttribute("..patient.id")
    doctor_id = factory.SelfAttribute("..doctor.id")
    tenant_id = factory.SelfAttribute("..tenant.id")
    start_time = factory.LazyFunction(
        lambda: datetime.utcnow() + timedelta(days=random.randint(1, 30))
    )
    end_time = factory.LazyAttribute(
        lambda o: o.start_time + timedelta(minutes=30)
    )
    appointment_type = factory.Iterator([
        "consultation", "procedure", "emergency", "follow_up",
    ])
    status = "scheduled"
    notes = factory.Faker("sentence", locale="es_CO")
    created_at = factory.LazyFunction(datetime.utcnow)

    class Params:
        confirmed = factory.Trait(status="confirmed")
        completed = factory.Trait(status="completed")
        cancelled = factory.Trait(status="cancelled")
        no_show = factory.Trait(status="no_show")
```

### 3.7 InvoiceFactory and TreatmentPlanFactory

```python
class InvoiceFactory(factory.Factory):
    class Meta:
        model = Invoice

    id = factory.LazyFunction(uuid.uuid4)
    patient_id = factory.SelfAttribute("..patient.id")
    tenant_id = factory.SelfAttribute("..tenant.id")
    invoice_number = factory.Sequence(lambda n: f"INV-{n:06d}")
    status = "draft"
    subtotal = factory.LazyFunction(lambda: round(random.uniform(50000, 500000), 2))
    tax_rate = 0.19  # Colombia IVA
    tax_amount = factory.LazyAttribute(lambda o: round(o.subtotal * o.tax_rate, 2))
    total = factory.LazyAttribute(lambda o: o.subtotal + o.tax_amount)
    currency = "COP"
    created_at = factory.LazyFunction(datetime.utcnow)


class TreatmentPlanFactory(factory.Factory):
    class Meta:
        model = TreatmentPlan

    id = factory.LazyFunction(uuid.uuid4)
    patient_id = factory.SelfAttribute("..patient.id")
    doctor_id = factory.SelfAttribute("..doctor.id")
    title = factory.Faker("sentence", nb_words=4, locale="es_CO")
    description = factory.Faker("paragraph", locale="es_CO")
    status = "draft"
    estimated_cost = factory.LazyFunction(
        lambda: round(random.uniform(100000, 5000000), 2)
    )
    created_at = factory.LazyFunction(datetime.utcnow)

    class Params:
        active = factory.Trait(status="active")
        completed = factory.Trait(status="completed")
```

---

## 4. Global Fixtures

Defined in `tests/conftest.py`. Available to all tests without explicit import.

### 4.1 Database Fixtures

```python
@pytest.fixture(scope="session")
async def test_db_engine():
    """Create async engine for test database. Session-scoped (created once)."""
    engine = create_async_engine(settings.TEST_DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine, test_tenant_schema):
    """
    Per-test database session with tenant schema isolation.
    Auto-rolls back after each test.
    """
    async with test_db_engine.connect() as conn:
        await conn.execute(text(f"SET search_path TO {test_tenant_schema}, public"))
        transaction = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await transaction.rollback()
        await session.close()
```

### 4.2 Tenant and User Fixtures

```python
@pytest.fixture
async def test_tenant(test_db_session) -> Tenant:
    """Provision a test tenant with professional plan."""
    tenant = TenantFactory()
    test_db_session.add(tenant)
    await test_db_session.flush()
    return tenant


@pytest.fixture
async def test_clinic_owner(test_db_session, test_tenant) -> User:
    """Clinic owner user for the test tenant."""
    user = UserFactory(clinic_owner=True, tenant_id=test_tenant.id)
    test_db_session.add(user)
    await test_db_session.flush()
    return user


@pytest.fixture
async def test_doctor(test_db_session, test_tenant) -> User:
    """Doctor user for the test tenant."""
    user = UserFactory(doctor=True, tenant_id=test_tenant.id)
    test_db_session.add(user)
    await test_db_session.flush()
    return user


@pytest.fixture
async def test_assistant(test_db_session, test_tenant) -> User:
    """Assistant user for the test tenant."""
    user = UserFactory(assistant=True, tenant_id=test_tenant.id)
    test_db_session.add(user)
    await test_db_session.flush()
    return user


@pytest.fixture
async def test_receptionist(test_db_session, test_tenant) -> User:
    """Receptionist user for the test tenant."""
    user = UserFactory(receptionist=True, tenant_id=test_tenant.id)
    test_db_session.add(user)
    await test_db_session.flush()
    return user
```

### 4.3 Patient Fixture

```python
@pytest.fixture
async def test_patient(test_db_session, test_tenant) -> Patient:
    """Patient record in the test tenant."""
    patient = PatientFactory(tenant_id=test_tenant.id)
    test_db_session.add(patient)
    await test_db_session.flush()
    return patient
```

### 4.4 Authenticated Client Fixtures

```python
@pytest.fixture
async def auth_headers_owner(test_clinic_owner, test_tenant) -> dict:
    """JWT auth headers for clinic_owner."""
    token = create_access_token(
        user_id=str(test_clinic_owner.id),
        tenant_id=str(test_tenant.id),
        role="clinic_owner",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def auth_headers_doctor(test_doctor, test_tenant) -> dict:
    """JWT auth headers for doctor."""
    token = create_access_token(
        user_id=str(test_doctor.id),
        tenant_id=str(test_tenant.id),
        role="doctor",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def async_client(test_db_session) -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx AsyncClient configured for FastAPI test server."""
    from app.main import app
    from app.deps import get_db_session

    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
```

---

## 5. Async Test Support

### 5.1 pytest-asyncio Configuration

All async tests are auto-detected. No `@pytest.mark.asyncio` decorator needed.

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### 5.2 Example Async Endpoint Test

```python
# tests/integration/test_api/test_patients/test_patient_create.py

async def test_create_patient_success(
    async_client: httpx.AsyncClient,
    auth_headers_doctor: dict,
    test_tenant: Tenant,
):
    payload = {
        "first_name": "Maria",
        "last_name": "Garcia Lopez",
        "document_type": "CC",
        "document_number": "1234567890",
        "birthdate": "1990-05-15",
        "gender": "F",
        "phone": "+573001234567",
        "email": "maria@example.com",
    }
    response = await async_client.post(
        "/api/v1/patients",
        json=payload,
        headers=auth_headers_doctor,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Maria"
    assert data["document_number"] == "1234567890"
    assert "id" in data


async def test_create_patient_duplicate_document(
    async_client: httpx.AsyncClient,
    auth_headers_doctor: dict,
    test_patient: Patient,
):
    payload = {
        "first_name": "Otro",
        "last_name": "Paciente",
        "document_type": test_patient.document_type,
        "document_number": test_patient.document_number,
        "birthdate": "1985-01-01",
        "gender": "M",
        "phone": "+573009999999",
    }
    response = await async_client.post(
        "/api/v1/patients",
        json=payload,
        headers=auth_headers_doctor,
    )
    assert response.status_code == 409
    assert response.json()["error"] == "duplicate_document"


async def test_create_patient_unauthorized(
    async_client: httpx.AsyncClient,
):
    response = await async_client.post(
        "/api/v1/patients",
        json={"first_name": "Test"},
    )
    assert response.status_code == 401
```

---

## 6. Mocking External Services

### 6.1 WhatsApp Business API

```python
@pytest.fixture
def mock_whatsapp(respx_mock):
    """Mock WhatsApp Business API calls."""
    respx_mock.post(
        "https://graph.facebook.com/v18.0/PHONE_NUMBER_ID/messages"
    ).respond(
        json={"messaging_product": "whatsapp", "messages": [{"id": "wamid.xxx"}]},
        status_code=200,
    )
    return respx_mock
```

### 6.2 Twilio SMS

```python
@pytest.fixture
def mock_twilio(respx_mock):
    """Mock Twilio SMS API."""
    respx_mock.post(
        re.compile(r"https://api\.twilio\.com/2010-04-01/Accounts/.*/Messages\.json")
    ).respond(
        json={"sid": "SM_test_sid", "status": "queued"},
        status_code=201,
    )
    return respx_mock
```

### 6.3 Email Service (SendGrid)

```python
@pytest.fixture
def mock_email(respx_mock):
    """Mock SendGrid email API."""
    respx_mock.post("https://api.sendgrid.com/v3/mail/send").respond(
        status_code=202,
        headers={"X-Message-Id": "test-message-id"},
    )
    return respx_mock
```

### 6.4 S3-Compatible Storage (MinIO)

```python
@pytest.fixture
def mock_s3():
    """Mock S3/MinIO storage using moto."""
    with mock_s3():
        s3_client = boto3.client(
            "s3",
            endpoint_url="http://localhost:9000",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        s3_client.create_bucket(Bucket="dentalos-test")
        yield s3_client
```

### 6.5 RabbitMQ (In-Memory Queue)

```python
@pytest.fixture
def mock_queue(monkeypatch):
    """Replace RabbitMQ publisher with in-memory collector."""
    published_messages = []

    async def fake_publish(queue_name: str, payload: dict):
        published_messages.append({"queue": queue_name, "payload": payload})

    monkeypatch.setattr("app.queue.publisher.publish", fake_publish)
    return published_messages
```

---

## 7. Frontend Testing

### 7.1 Stack

| Tool | Version | Purpose |
|------|---------|---------|
| Vitest | >= 2.0 | Unit and component test runner |
| React Testing Library | >= 15.0 | Component rendering and interaction |
| @testing-library/user-event | >= 14.0 | Realistic user interaction simulation |
| MSW (Mock Service Worker) | >= 2.0 | API mocking at the network level |
| Playwright | >= 1.44 | E2E browser testing |
| @axe-core/playwright | >= 4.9 | Accessibility testing in E2E |

### 7.2 Frontend Directory Structure

```
frontend/
  src/
    __tests__/                     # Co-located tests preferred, this is fallback
  tests/
    setup.ts                       # Vitest global setup (MSW, providers)
    mocks/
      handlers.ts                  # MSW request handlers
      server.ts                    # MSW server instance
    e2e/
      auth.spec.ts                 # Login/register flows
      patients.spec.ts             # Patient CRUD flows
      odontogram.spec.ts           # Odontogram interaction (critical E2E)
      appointments.spec.ts         # Appointment booking flow
      billing.spec.ts              # Invoice creation flow
    utils/
      render.tsx                   # Custom render with providers (auth, query, router)
      factories.ts                 # Frontend test data factories (TypeScript)
```

### 7.3 Vitest Configuration

```typescript
// vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}", "tests/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.d.ts",
        "src/**/*.test.{ts,tsx}",
        "src/**/index.ts",      // barrel files
        "src/types/**",
      ],
      thresholds: {
        lines: 70,
        branches: 65,
        functions: 70,
        statements: 70,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

### 7.4 Custom Render with Providers

```tsx
// tests/utils/render.tsx
import { render, RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/providers/auth-provider";

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

interface CustomRenderOptions extends RenderOptions {
  user?: { id: string; role: string; tenantId: string };
}

export function renderWithProviders(
  ui: React.ReactElement,
  options: CustomRenderOptions = {},
) {
  const { user, ...renderOptions } = options;
  const queryClient = createTestQueryClient();

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <AuthProvider testUser={user}>{children}</AuthProvider>
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}
```

### 7.5 MSW API Mocking

```typescript
// tests/mocks/handlers.ts
import { http, HttpResponse } from "msw";

export const handlers = [
  http.get("/api/v1/auth/me", () => {
    return HttpResponse.json({
      id: "user-1",
      email: "doctor@clinica.co",
      role: "doctor",
      tenant_id: "tenant-1",
      first_name: "Carlos",
      last_name: "Ramirez",
    });
  }),

  http.get("/api/v1/patients", ({ request }) => {
    const url = new URL(request.url);
    const page = url.searchParams.get("page") || "1";
    return HttpResponse.json({
      items: [
        { id: "p-1", first_name: "Maria", last_name: "Garcia", document_number: "123" },
        { id: "p-2", first_name: "Juan", last_name: "Lopez", document_number: "456" },
      ],
      total: 2,
      page: parseInt(page),
      page_size: 20,
    });
  }),

  http.get("/api/v1/patients/:patientId/odontogram", ({ params }) => {
    return HttpResponse.json({
      patient_id: params.patientId,
      dentition: "adult",
      teeth: [],  // Populated per test
      conditions: [],
    });
  }),
];
```

### 7.6 Playwright E2E Configuration

```typescript
// playwright.config.ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "tablet", use: { ...devices["iPad Pro 11"] } },  // Primary clinical device
    { name: "mobile", use: { ...devices["iPhone 14"] } },
  ],
  webServer: [
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
```

**Critical E2E Scenarios:**

| Test | Priority | Description |
|------|----------|-------------|
| Login flow | Critical | Email + password login, redirect to dashboard |
| Patient creation | Critical | Full form submission, validation, success toast |
| Odontogram interaction | Critical | Tap tooth zone, select condition, verify visual update |
| Appointment booking | High | Select doctor, date, time slot, confirm |
| Treatment plan approval | High | View plan, sign, verify signed status |
| Consent form signing | High | Open consent, draw signature, submit |

---

## 8. Coverage Targets

| Scope | Target | Minimum | Enforcement |
|-------|--------|---------|-------------|
| Backend (Python) | 85% | 80% | `--cov-fail-under=80` in pytest |
| Frontend unit/component | 75% | 70% | Vitest thresholds in config |
| E2E (Playwright) | N/A | Critical paths covered | CI check for test pass |

**Coverage exclusions:**

- Migration files (`alembic/versions/`)
- Configuration/settings modules
- Type stubs and interfaces
- Generated code (Pydantic models from OpenAPI)
- CLI scripts

---

## 9. CI/CD Pipeline (GitHub Actions)

### 9.1 Workflow File

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # ─── Backend Linting ───────────────────────────────
  backend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: pip install ruff black mypy
      - name: Ruff lint
        run: ruff check backend/
      - name: Ruff format check
        run: ruff format --check backend/
      - name: Mypy type check
        run: mypy backend/app/ --config-file backend/pyproject.toml

  # ─── Backend Tests ─────────────────────────────────
  backend-test:
    runs-on: ubuntu-latest
    needs: backend-lint
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: dentalos_test
          POSTGRES_USER: dentalos_test
          POSTGRES_PASSWORD: test
        ports:
          - 5433:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6380:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: pip install -r backend/requirements.txt -r backend/requirements-test.txt
      - name: Run migrations
        run: cd backend && alembic upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://dentalos_test:test@localhost:5433/dentalos_test
      - name: Run tests
        run: cd backend && pytest --cov-report=xml
        env:
          ENVIRONMENT: test
          DATABASE_URL: postgresql+asyncpg://dentalos_test:test@localhost:5433/dentalos_test
          REDIS_URL: redis://localhost:6380/0
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: backend/coverage.xml
          flags: backend

  # ─── Frontend Linting ──────────────────────────────
  frontend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - name: ESLint
        run: cd frontend && npx eslint src/ --max-warnings 0
      - name: Prettier check
        run: cd frontend && npx prettier --check "src/**/*.{ts,tsx,css}"
      - name: TypeScript check
        run: cd frontend && npx tsc --noEmit

  # ─── Frontend Unit Tests ───────────────────────────
  frontend-test:
    runs-on: ubuntu-latest
    needs: frontend-lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - name: Run Vitest
        run: cd frontend && npx vitest run --coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: frontend/coverage/lcov.info
          flags: frontend

  # ─── E2E Tests ─────────────────────────────────────
  e2e-test:
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-test]
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: dentalos_test
          POSTGRES_USER: dentalos_test
          POSTGRES_PASSWORD: test
        ports:
          - 5433:5432
      redis:
        image: redis:7-alpine
        ports:
          - 6380:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: pip install -r backend/requirements.txt
      - run: cd frontend && npm ci
      - name: Install Playwright browsers
        run: cd frontend && npx playwright install --with-deps chromium
      - name: Start backend
        run: cd backend && uvicorn app.main:app --port 8000 &
        env:
          ENVIRONMENT: test
          DATABASE_URL: postgresql+asyncpg://dentalos_test:test@localhost:5433/dentalos_test
          REDIS_URL: redis://localhost:6380/0
      - name: Start frontend
        run: cd frontend && npm run dev &
        env:
          NEXT_PUBLIC_API_URL: http://localhost:8000
      - name: Wait for servers
        run: |
          npx wait-on http://localhost:8000/health http://localhost:3000 --timeout 60000
      - name: Run Playwright
        run: cd frontend && npx playwright test --project=chromium
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

---

## 10. Test Commands and Conventions

### 10.1 Command Reference

```bash
# ─── Backend ──────────────────────────────────────────
make test                    # Run all backend tests
make test-unit               # pytest -m unit
make test-integration        # pytest -m integration
make test-e2e                # pytest -m e2e
make test-cov                # Run with HTML coverage report
make test-watch              # pytest-watch (re-run on file change)
make test-file FILE=tests/integration/test_api/test_patients/test_patient_create.py
make test-verbose            # pytest -v --tb=long

# ─── Frontend ─────────────────────────────────────────
npm run test                 # vitest run
npm run test:watch           # vitest (watch mode)
npm run test:coverage        # vitest run --coverage
npm run test:ui              # vitest --ui (browser UI)
npm run test:e2e             # playwright test
npm run test:e2e:headed      # playwright test --headed
npm run test:e2e:tablet      # playwright test --project=tablet
```

### 10.2 Naming Conventions

| Convention | Pattern | Example |
|------------|---------|---------|
| Test file | `test_{module}.py` / `{Component}.test.tsx` | `test_patient_create.py`, `PatientForm.test.tsx` |
| Test function | `test_{action}_{scenario}` | `test_create_patient_success`, `test_create_patient_duplicate_document` |
| Test class | `Test{Feature}` | `TestPatientCreate`, `TestOdontogramUpdate` |
| Factory | `{Model}Factory` | `PatientFactory`, `AppointmentFactory` |
| Fixture | `test_{entity}` or `{entity}_fixture` | `test_patient`, `test_doctor` |

### 10.3 Test Conventions

1. **Arrange-Act-Assert** pattern for all tests.
2. **One assertion concept per test** (multiple asserts on the same concept are fine).
3. **No test interdependence.** Each test must be runnable in isolation.
4. **Factories over raw data.** Always use factories to create test data; never hardcode dictionaries.
5. **Descriptive test names.** The test name should describe the scenario, not the implementation.
6. **Mark slow tests.** Any test taking over 2 seconds gets `@pytest.mark.slow`.
7. **No sleeps.** Use `asyncio` waits with timeouts, never `time.sleep`.
8. **Freeze time for date tests.** Use `freezegun` when testing date-dependent logic.

---

## Out of Scope

This spec explicitly does NOT cover:

- Load testing and performance benchmarking (separate `infra/performance-testing.md` if needed)
- Security penetration testing and vulnerability scanning
- Visual regression testing (screenshot comparison)
- Contract testing between frontend and backend (Pact or similar)
- Chaos engineering and failure injection testing
- Database migration testing (covered in `infra/database-architecture.md`)
- Monitoring and alerting for test infrastructure

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
