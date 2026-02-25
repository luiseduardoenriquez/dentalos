# Digital Signature (P-17)

---

## Overview

**Feature:** Registrar y verificar firmas digitales electronicas para documentos clinicos en DentalOS (consentimientos, referidos, evoluciones, cotizaciones aprobadas). Implementa firma electronica conforme a la Ley 527/1999 de Colombia: canvas SVG firmado en dispositivo, hash SHA-256 del payload del documento, timestamp con hora del servidor y entrada en audit log inmutable. La firma vincula criptograficamente al firmante con el documento y el momento de firma.

**Domain:** patients

**Priority:** High

**Dependencies:** consents (para firma de consentimientos), patient-referral (P-15 — firma al completar referido), billing (para firma de cotizaciones aprobadas), I-02 (authentication-rules.md), database-architecture.md (`digital_signatures`, `document_signature_events`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:**
  - POST (crear firma): doctor, clinic_owner, patient (para firma del paciente en consentimientos y cotizaciones)
  - GET (verificar firma): doctor, clinic_owner, assistant (no modifica datos)
- **Tenant context:** Required — resuelto desde JWT. Para firmas de pacientes en el portal, el JWT del portal incluye `tenant_id`.
- **Special rules:**
  - Un usuario solo puede firmar como si mismo. No puede firmar en nombre de otro.
  - El documento a firmar debe existir, pertenecer al tenant y estar en un estado que permita firma (ej. referido en `in_progress`, consentimiento en `pending_signature`).
  - Si el documento requiere firma de multiples partes, cada parte firma por separado.

---

## Endpoints

### Registrar Firma Digital

```
POST /api/v1/signatures
```

### Verificar Firma Digital

```
GET /api/v1/signatures/{signature_id}
```

**Rate Limiting:**
- POST: 20 requests por minuto por usuario (firmar es accion deliberada, no masiva)
- GET: Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes (POST) | string | Formato de request | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters (GET)

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| signature_id | Yes | UUID | UUID v4 valido | ID de la firma a verificar | sig_9a1b2c3d-e4f5-6789-abcd-ef0123456789 |

### Query Parameters

N/A

### Request Body Schema (POST)

```json
{
  "document_type": "string (required) — tipo del documento firmado: consent | referral | evolution | quotation",
  "document_id": "UUID (required) — ID del documento a firmar",
  "signer_role": "string (required) — rol del firmante en el contexto del documento: doctor | patient | clinic_owner",
  "canvas_data": "string (required) — imagen SVG o PNG base64 de la firma manuscrita capturada en canvas",
  "canvas_format": "string (required) — enum: svg | png_base64",
  "document_hash_client": "string (required) — SHA-256 del payload del documento calculado por el cliente (para verificacion cruzada)",
  "ip_address": "string (optional) — IP del dispositivo del firmante (puede capturarse en el servidor tambien)",
  "device_info": "string (optional) — user agent o identificador del dispositivo, max 500 chars"
}
```

**Nota tecnica — hash del documento:**
El `document_hash_client` se calcula sobre el contenido canonico del documento en el momento de la firma. El servidor calcula su propio hash (`document_hash_server`) del mismo documento desde la base de datos y los compara. Si difieren, la firma es rechazada (el documento fue modificado entre que el usuario lo vio y lo firmo).

**Example Request:**
```json
{
  "document_type": "referral",
  "document_id": "ref_1a2b3c4d-e5f6-7890-abcd-ef0123456789",
  "signer_role": "doctor",
  "canvas_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "canvas_format": "png_base64",
  "document_hash_client": "a3f5c8d2e1b4a7f9c6d3e0b5a2f8c1d4e7b0a3f6c9d2e5b8a1f4c7d0e3b6a9",
  "device_info": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) DentalOS/2.1.0"
}
```

---

## Response

### Success Response — POST

**Status:** 201 Created

**Schema:**
```json
{
  "id": "UUID",
  "document_type": "string",
  "document_id": "UUID",
  "signer_id": "UUID",
  "signer_name": "string",
  "signer_role": "string",
  "document_hash_server": "string — SHA-256 del documento al momento de firma",
  "signature_hash": "string — SHA-256 de (document_hash + signer_id + timestamp)",
  "canvas_url": "string — URL firmada S3 de la imagen de la firma, 24h expiry",
  "signed_at": "ISO8601 — timestamp del servidor (no del cliente)",
  "ip_address": "string",
  "device_info": "string | null",
  "legal_statement": "string — declaracion legal segun Ley 527/1999 Colombia",
  "verified": true
}
```

**Example:**
```json
{
  "id": "sig_9a1b2c3d-e4f5-6789-abcd-ef0123456789",
  "document_type": "referral",
  "document_id": "ref_1a2b3c4d-e5f6-7890-abcd-ef0123456789",
  "signer_id": "usr_550e8400-e29b-41d4-a716-446655440000",
  "signer_name": "Dra. Ana Martinez",
  "signer_role": "doctor",
  "document_hash_server": "a3f5c8d2e1b4a7f9c6d3e0b5a2f8c1d4e7b0a3f6c9d2e5b8a1f4c7d0e3b6a9",
  "signature_hash": "7f3a9c2d5e8b1f4a7d0e3c6b9f2a5d8e1c4b7f0a3e6c9d2b5a8f1c4d7e0b3a6",
  "canvas_url": "https://s3.amazonaws.com/dentalos-storage/tn_7c9e/signatures/sig_9a1b.png?X-Amz-Signature=abc&X-Amz-Expires=86400",
  "signed_at": "2026-02-24T16:30:00.123456Z",
  "ip_address": "190.25.14.87",
  "device_info": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) DentalOS/2.1.0",
  "legal_statement": "Esta firma electronica tiene plena validez legal conforme a la Ley 527 de 1999 de Colombia. El firmante Dra. Ana Martinez (ID: usr_550e...) acepta y ratifica el documento ref_1a2b... con hash SHA-256 a3f5c8d2... en fecha 2026-02-24T16:30:00Z.",
  "verified": true
}
```

### Success Response — GET (Verificar firma)

**Status:** 200 OK

**Schema:**
```json
{
  "id": "UUID",
  "document_type": "string",
  "document_id": "UUID",
  "signer_id": "UUID",
  "signer_name": "string",
  "signer_role": "string",
  "document_hash_server": "string",
  "signature_hash": "string",
  "canvas_url": "string — URL firmada S3, 1h expiry",
  "signed_at": "ISO8601",
  "ip_address": "string",
  "verified": "boolean",
  "verification_result": {
    "hash_match": "boolean — hash del documento en DB coincide con hash actual del documento",
    "document_unmodified": "boolean — el documento no fue alterado tras la firma",
    "signer_active": "boolean — el firmante sigue siendo usuario activo del tenant",
    "verified_at": "ISO8601"
  }
}
```

**Example (verificacion exitosa):**
```json
{
  "id": "sig_9a1b2c3d-e4f5-6789-abcd-ef0123456789",
  "document_type": "referral",
  "document_id": "ref_1a2b3c4d-e5f6-7890-abcd-ef0123456789",
  "signer_id": "usr_550e8400-e29b-41d4-a716-446655440000",
  "signer_name": "Dra. Ana Martinez",
  "signer_role": "doctor",
  "document_hash_server": "a3f5c8d2e1b4a7f9c6d3e0b5a2f8c1d4e7b0a3f6c9d2e5b8a1f4c7d0e3b6a9",
  "signature_hash": "7f3a9c2d5e8b1f4a7d0e3c6b9f2a5d8e1c4b7f0a3e6c9d2b5a8f1c4d7e0b3a6",
  "canvas_url": "https://s3.amazonaws.com/...",
  "signed_at": "2026-02-24T16:30:00.123456Z",
  "ip_address": "190.25.14.87",
  "verified": true,
  "verification_result": {
    "hash_match": true,
    "document_unmodified": true,
    "signer_active": true,
    "verified_at": "2026-02-24T17:00:00Z"
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Formato de canvas invalido, `canvas_data` vacio, `canvas_format` desconocido, o hash SHA-256 con formato invalido.

**Example:**
```json
{
  "error": "invalid_signature_data",
  "message": "Los datos de la firma no son validos.",
  "details": {
    "canvas_data": ["El campo de firma no puede estar vacio."],
    "document_hash_client": ["El hash debe ser SHA-256 hexadecimal de 64 caracteres."]
  }
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** El usuario intenta firmar un documento que no le corresponde (ej. paciente A intenta firmar como paciente B, o doctor intenta firmar como `patient`).

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para firmar este documento en el rol especificado."
}
```

#### 404 Not Found
**When:** El documento referenciado (`document_type` + `document_id`) no existe en el tenant.

```json
{
  "error": "document_not_found",
  "message": "El documento a firmar no fue encontrado."
}
```

#### 409 Conflict
**When:** El firmante ya firmo este documento (no se permite duplicar firmas del mismo usuario en el mismo documento).

```json
{
  "error": "already_signed",
  "message": "Ya has firmado este documento. La firma fue registrada el 2026-02-24T16:30:00Z."
}
```

#### 422 Unprocessable Entity
**When:** El hash del cliente no coincide con el hash calculado por el servidor (documento fue modificado).

```json
{
  "error": "document_hash_mismatch",
  "message": "El documento fue modificado desde que fue cargado para firma. Por favor, recargue el documento y firme nuevamente.",
  "details": {
    "hash_client": "a3f5c8d2...",
    "hash_server": "b9e2d4f1..."
  }
}
```

**When:** El documento esta en un estado que no admite firma (ej. referido `cancelled`, consentimiento `revoked`).

```json
{
  "error": "document_not_signable",
  "message": "El documento no puede ser firmado en su estado actual: cancelled."
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error al subir imagen de firma a S3, fallo en calculo de hash del servidor.

---

## Business Logic

**Step-by-step process (POST — registrar firma):**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Validar body con Pydantic:
   - `document_type` en enum permitido.
   - `document_id` UUID v4 valido.
   - `signer_role` en enum: doctor, patient, clinic_owner.
   - `canvas_data` no vacio.
   - `canvas_format` en enum: svg, png_base64.
   - `document_hash_client`: exactamente 64 caracteres hexadecimales (SHA-256).
3. Verificar que el `signer_role` coincide con el rol del usuario autenticado en el contexto del documento:
   - Si `signer_role = "doctor"`: el JWT debe tener rol `doctor` o `clinic_owner`.
   - Si `signer_role = "patient"`: el JWT debe ser del portal del paciente.
   - Si el firmante intenta asumir un rol que no le corresponde: 403.
4. Resolver el documento segun `document_type`:
   - `consent` → tabla `consents`
   - `referral` → tabla `referrals`
   - `evolution` → tabla `clinical_records`
   - `quotation` → tabla `quotations`
   - Verificar que el documento existe y pertenece al tenant. Si no, 404.
5. Verificar que el documento esta en un estado firmable:
   - `referral`: `in_progress` o `accepted`
   - `consent`: `pending_signature`
   - `evolution`: `draft`
   - `quotation`: `sent` o `approved`
   - Si el estado no es firmable: 422.
6. Verificar que el usuario (`user_id`) no ha firmado ya este documento: `SELECT 1 FROM digital_signatures WHERE document_type = :type AND document_id = :id AND signer_id = :user_id`. Si existe, 409.
7. **Calcular `document_hash_server`:**
   - Serializar el documento en JSON canonico (llaves ordenadas, sin campos de audit como `updated_at`).
   - Calcular SHA-256 del JSON canonico serializado.
   - Comparar con `document_hash_client`. Si difieren: 422 con `document_hash_mismatch`.
8. **Calcular `signature_hash`:**
   - `payload = f"{document_hash_server}|{user_id}|{timestamp_utc_iso}"`
   - `signature_hash = SHA-256(payload)`
9. **Procesar imagen de firma canvas:**
   - Si `canvas_format = "png_base64"`: decodificar base64, verificar que es imagen PNG valida.
   - Si `canvas_format = "svg"`: validar que es SVG bien formado (no ejecutar, solo parsear estructura).
   - Subir imagen a S3: `{tenant_id}/signatures/{signature_uuid}.{ext}`.
   - Generar URL firmada con expiracion de 24 horas.
10. Construir `legal_statement` en espanol: texto que incluye nombre del firmante, ID del documento, hash del documento y timestamp. Este texto forma parte del registro inmutable.
11. Insertar en `digital_signatures`:
    - `id = signature_uuid`
    - `document_type`, `document_id`, `signer_id = user_id`, `signer_role`
    - `document_hash_server`, `signature_hash`
    - `canvas_s3_key`, `canvas_format`
    - `signed_at = timestamp_utc` (hora del servidor, no del cliente)
    - `ip_address` (del request, del servidor si no se provee en body)
    - `device_info`, `legal_statement`
12. Insertar en `document_signature_events` (log inmutable, sin UPDATE/DELETE): evento de firma con todos los datos relevantes.
13. **Actualizar estado del documento si todas las firmas requeridas estan completas:**
    - Segun tipo de documento, verificar si faltan mas firmas.
    - Si `referral` y ambos doctores firmaron: actualizar `status = 'completed'`.
    - Si `consent` y el paciente firmo: actualizar `status = 'signed'`.
14. Registrar en audit log: `patients.digital_signature.created` (PHI).
15. Retornar 201 Created con datos de la firma y `legal_statement`.

**Step-by-step process (GET — verificar firma):**

1. Validar JWT y extraer `tenant_id`, `role`.
2. Verificar rol `doctor`, `clinic_owner` o `assistant`. Si no, 403.
3. Buscar firma en `digital_signatures` donde `id = signature_id`. Si no existe o es de otro tenant, 404.
4. Re-calcular `document_hash_server` del documento actual (en su estado actual en BD).
5. Comparar con el `document_hash_server` almacenado en la firma.
   - Si coinciden: `document_unmodified = true`.
   - Si difieren: `document_unmodified = false` (el documento fue alterado despues de la firma — alerta).
6. Verificar que el firmante sigue siendo usuario activo del tenant: `signer_active = true/false`.
7. Generar URL firmada del canvas con expiracion de 1 hora.
8. Retornar 200 con resultado de verificacion.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| document_type | Enum: consent, referral, evolution, quotation | "Tipo de documento no valido." |
| document_id | UUID v4 | "El ID del documento no es valido." |
| signer_role | Enum: doctor, patient, clinic_owner | "El rol del firmante no es valido." |
| canvas_data | No vacio, max 5MB en base64 | "La firma manuscrita es obligatoria." |
| canvas_format | Enum: svg, png_base64 | "Formato de canvas no valido. Use: svg o png_base64." |
| document_hash_client | Exactamente 64 caracteres hexadecimales | "El hash del documento debe ser SHA-256 de 64 caracteres hexadecimales." |

**Business Rules:**

- El `signed_at` siempre usa la hora del servidor (UTC). El timestamp del cliente no se usa para la firma legal.
- El `signature_hash` se calcula con: SHA-256(`document_hash_server` + `|` + `user_id` + `|` + `signed_at_iso`). Es unico y verificable.
- La imagen canvas se almacena como evidencia visual de la firma pero el valor legal es el `signature_hash`.
- Los registros en `digital_signatures` y `document_signature_events` son INMUTABLES: no se pueden actualizar ni eliminar (solo INSERT).
- La firma conforme a Ley 527/1999 (Colombia) requiere: vinculacion al firmante, integridad del mensaje (hash), y fecha/hora verificable (timestamp servidor).
- La tabla `document_signature_events` actua como audit trail inmutable adicional, separada de `digital_signatures`.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Doctor firma el mismo referido dos veces | 409 Conflict — ya firmo este documento |
| Documento modificado entre carga y firma | 422 document_hash_mismatch |
| Firmante desactivado posteriormente | GET verificacion muestra `signer_active: false` (informativo) |
| SVG con scripts maliciosos (XSS en SVG) | Rechazar — sanitizar SVG, eliminar elementos `<script>` antes de almacenar |
| Canvas data demasiado grande (> 5MB base64) | 400 Bad Request |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `digital_signatures`: INSERT — registro inmutable de la firma (NO UPDATE, NO DELETE)
- `document_signature_events`: INSERT — evento de audit inmutable
- Tabla del documento firmado (ej. `referrals`, `consents`): UPDATE — `status` si todas las firmas fueron completadas

**Example query (SQLAlchemy):**
```python
from sqlalchemy import insert, select
import hashlib
import json
from datetime import datetime, timezone

# Calcular hash del documento en servidor
document_data = serialize_document_canonical(document)
document_hash_server = hashlib.sha256(
    json.dumps(document_data, sort_keys=True, ensure_ascii=False).encode()
).hexdigest()

# Verificar coincidencia con hash del cliente
if document_hash_server != body.document_hash_client:
    raise DocumentHashMismatchException(
        hash_client=body.document_hash_client,
        hash_server=document_hash_server
    )

# Calcular signature hash
signed_at = datetime.now(timezone.utc)
signature_payload = f"{document_hash_server}|{user_id}|{signed_at.isoformat()}"
signature_hash = hashlib.sha256(signature_payload.encode()).hexdigest()

async with session.begin():
    # Insertar firma (INMUTABLE)
    await session.execute(
        insert(DigitalSignature).values(
            id=signature_uuid,
            document_type=body.document_type,
            document_id=body.document_id,
            tenant_id=tenant_id,
            signer_id=user_id,
            signer_role=body.signer_role,
            document_hash_server=document_hash_server,
            signature_hash=signature_hash,
            canvas_s3_key=canvas_s3_path,
            canvas_format=body.canvas_format,
            signed_at=signed_at,
            ip_address=request.client.host,
            device_info=body.device_info,
            legal_statement=build_legal_statement(
                signer_name=user.full_name,
                document_id=body.document_id,
                document_hash=document_hash_server,
                signed_at=signed_at,
            ),
        )
    )

    # Insertar evento de audit inmutable
    await session.execute(
        insert(DocumentSignatureEvent).values(
            signature_id=signature_uuid,
            event_type="signature_created",
            tenant_id=tenant_id,
            signer_id=user_id,
            document_type=body.document_type,
            document_id=body.document_id,
            document_hash=document_hash_server,
            ip_address=request.client.host,
            occurred_at=signed_at,
        )
    )
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:document:{document_type}:{document_id}:signatures`: DELETE (invalidacion al agregar nueva firma)

**Cache TTL:** N/A (invalidacion)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications.signature_completed | document_signed | { document_type, document_id, signer_id, signer_name, signed_at, tenant_id, all_signatures_complete } | Al registrar firma exitosamente |

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** digital_signature
- **PHI involved:** Yes — la firma vincula a una persona con un documento clinico

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | signature_received | Otras partes que deben firmar el mismo documento | Al registrar firma |
| in-app | document_fully_signed | Todos los firmantes del documento | Cuando todas las firmas requeridas estan completas |

---

## Performance

### Expected Response Time
- **Target (POST):** < 600ms (incluye hash calculation, S3 upload de canvas, insert DB)
- **Maximum acceptable (POST):** < 1500ms
- **Target (GET):** < 300ms (incluye re-calculo de hash para verificacion)

### Caching Strategy
- **Strategy:** Sin cache para firmas (datos inmutables y de auditoria — cada acceso debe ser fresco para verificacion).
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** N/A

### Database Performance

**Queries executed (POST):** 5-7 (verificar documento, verificar firma existente, insert firma, insert evento, update documento si completo)

**Indexes required:**
- `digital_signatures.id` — PRIMARY KEY
- `digital_signatures.(document_type, document_id)` — INDEX COMPUESTO
- `digital_signatures.(document_type, document_id, signer_id)` — INDEX COMPUESTO UNIQUE (prevenir firma duplicada)
- `digital_signatures.tenant_id` — INDEX
- `document_signature_events.signature_id` — INDEX
- `document_signature_events.document_id` — INDEX

**N+1 prevention:** No aplica. Las firmas son accedidas individualmente.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| document_type | Pydantic Enum estricto | |
| document_id | Pydantic UUID | |
| canvas_data (SVG) | Sanitizar con `defusedxml` — eliminar `<script>`, `<object>`, event handlers | Prevenir XSS embebido en SVG |
| canvas_data (base64) | Verificar que decodifica a imagen PNG valida antes de subir | |
| document_hash_client | Pydantic str, regex `^[a-f0-9]{64}$` | Solo hexadecimal lowercase 64 chars |
| device_info | Pydantic str, strip, max_length=500 | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**SVG sanitization:** Usar `defusedxml` para parsear SVG y eliminar elementos y atributos peligrosos antes de almacenar en S3. El SVG nunca se sirve directamente al browser sin Content-Type forzado a `image/svg+xml` con `Content-Disposition: attachment`.

**Output encoding:** Serializacion Pydantic para respuesta JSON.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** La firma digital vincula a una persona identificada con un documento clinico. El `legal_statement` contiene nombre del firmante y referencia al documento. La imagen canvas puede contener la firma manuscrita del paciente o medico.

**Audit requirement:** All access logged — creacion y verificacion de firmas auditadas por ser PHI con valor legal.

**Inmutabilidad legal:** Los registros de `digital_signatures` y `document_signature_events` nunca se modifican ni eliminan. Si se necesita "revocar" una firma (ej. consentimiento retirado por el paciente), se agrega un evento de revocacion en `document_signature_events`, no se elimina el registro original.

---

## Testing

### Test Cases

#### Happy Path
1. Doctor firma referido exitosamente
   - **Given:** Referido en estado `in_progress`, usuario `doctor` que es parte del referido, canvas PNG base64 valido, hash correcto
   - **When:** POST /api/v1/signatures con datos correctos
   - **Then:** 201 Created, `signature_hash` generado, `canvas_url` es URL S3 firmada, `signed_at` es timestamp del servidor, `legal_statement` incluye nombre del firmante

2. Ambos doctores firman referido — estado cambia a completed
   - **Given:** Referido con firma del doctor remitente ya registrada
   - **When:** POST firma del doctor receptor
   - **Then:** 201 Created, referido actualizado a `status: "completed"`

3. Verificar firma no alterada (GET)
   - **Given:** Firma existente, documento no modificado despues de firma
   - **When:** GET /api/v1/signatures/{signature_id}
   - **Then:** 200 OK, `verified: true`, `verification_result.document_unmodified: true`, `hash_match: true`

4. Verificar firma cuando documento fue alterado (GET)
   - **Given:** Firma existente, pero el documento fue modificado despues
   - **When:** GET /api/v1/signatures/{signature_id}
   - **Then:** 200 OK, `verified: true` (firma existe), `verification_result.document_unmodified: false` (ALERTA)

5. Firma con canvas SVG
   - **Given:** Canvas en formato SVG valido sin scripts
   - **When:** POST con `canvas_format: "svg"`
   - **Then:** 201 Created, SVG almacenado en S3

#### Edge Cases
1. Hash del cliente no coincide con hash del servidor
   - **Given:** El documento fue modificado entre que se cargo y se intenta firmar
   - **When:** POST con `document_hash_client` desactualizado
   - **Then:** 422 document_hash_mismatch con ambos hashes en el detalle

2. Timestamp del cliente vs servidor
   - **Given:** Cliente envia timestamp incorrecto (sin campo — no hay `signed_at` en el body)
   - **When:** POST firma
   - **Then:** 201, `signed_at` usa timestamp del servidor correctamente

3. SVG con script malicioso
   - **Given:** SVG con `<script>alert('xss')</script>` embebido
   - **When:** POST con `canvas_format: "svg"`
   - **Then:** 400 Bad Request — "El archivo SVG contiene elementos no permitidos."

#### Error Cases
1. Firma duplicada del mismo usuario en el mismo documento
   - **Given:** Doctor ya firmo el referido
   - **When:** POST firma nuevamente
   - **Then:** 409 Conflict con fecha de firma original

2. Documento en estado no firmable
   - **Given:** Referido en estado `cancelled`
   - **When:** POST firma
   - **Then:** 422 document_not_signable con estado actual

3. Firmante intenta firmar como rol incorrecto
   - **Given:** Usuario con rol `doctor` en JWT, `signer_role: "patient"` en body
   - **When:** POST firma
   - **Then:** 403 Forbidden

4. Documento de otro tenant
   - **Given:** `document_id` pertenece a tenant B, usuario en tenant A
   - **When:** POST firma
   - **Then:** 404 Not Found

5. Hash malformado (no SHA-256)
   - **Given:** `document_hash_client: "abc123"` (menos de 64 chars)
   - **When:** POST firma
   - **Then:** 400 Bad Request

6. Canvas vacio (usuario no firmo)
   - **Given:** `canvas_data: ""`
   - **When:** POST firma
   - **Then:** 400 Bad Request — "La firma manuscrita es obligatoria."

### Test Data Requirements

**Users:** Un `doctor` remitente, un `doctor` receptor, un `clinic_owner`.

**Documents:** Un referido en `in_progress`, un referido en `cancelled`, un consentimiento en `pending_signature`.

**Signatures:** Ninguna inicialmente. Seed para test de duplicado: firma preexistente del doctor remitente en el referido.

**Canvas samples:** PNG base64 valido (imagen de firma real), SVG valido, SVG con script malicioso, base64 invalido.

### Mocking Strategy

- **S3:** moto o localstack para upload de canvas
- **hashlib:** No mockear (usar hashes reales en todos los tests)
- **Clock:** Mockear `datetime.utcnow()` para tests que verifican `signed_at`
- **Redis:** fakeredis para rate limiting
- **defusedxml:** No mockear — usar libreria real con SVGs de prueba

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST registra firma con `signature_hash` calculado como SHA-256(`document_hash_server|user_id|signed_at`)
- [ ] `document_hash_client` comparado con `document_hash_server` — mismatch retorna 422
- [ ] `signed_at` siempre usa timestamp del servidor (UTC)
- [ ] Imagen canvas subida a S3, URL firmada 24h en respuesta
- [ ] SVGs sanitizados con defusedxml antes de almacenar
- [ ] Firma duplicada del mismo usuario retorna 409
- [ ] Documento en estado no firmable retorna 422
- [ ] Registro en `digital_signatures` y `document_signature_events` es inmutable (no DELETE, no UPDATE)
- [ ] Si todas las firmas requeridas estan, el documento actualiza su estado automaticamente
- [ ] GET verifica si el documento fue alterado tras la firma (`document_unmodified`)
- [ ] `legal_statement` en espanol incluido en respuesta y almacenado
- [ ] PHI auditado en audit log
- [ ] All test cases pass
- [ ] Performance targets met (< 1500ms POST)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Firma electronica avanzada con certificado digital PKI (certificado emitido por entidad certificadora — post-MVP)
- Firma en PDF con campo de firma embebido (PDF signing)
- Revocacion de firma (se puede agregar como evento en `document_signature_events` pero fuera de esta spec)
- Firma de consentimientos especificos (flujo de UI — la mecanica de firma es la misma)
- Firma biometrica (huella dactilar — hardware no estandarizado)
- Interoperabilidad con sistemas externos de firma electronica (DocuSign, Hellosign)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schema con todos los campos de firma)
- [x] All outputs defined (response POST y GET con verification_result)
- [x] API contract defined (OpenAPI compatible, 2 endpoints)
- [x] Validation rules stated (hash format, canvas format, signer role)
- [x] Error cases enumerated (hash mismatch, duplicado, estado invalido, SVG malicioso, canvas vacio)
- [x] Auth requirements explicit (role diferenciado POST/GET, signer_role validation)
- [x] Side effects listed (DB inmutable, S3, queue, audit log PHI)
- [x] Examples provided (firma de referido + respuesta de verificacion)

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (patients domain, firmas cross-domain via document_type)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models: tablas inmutables sin UPDATE/DELETE — conforme a requisitos legales

### Hook 3: Security & Privacy
- [x] Auth level stated (signer_role debe coincidir con rol real del JWT)
- [x] SVG sanitization con defusedxml (prevenir XSS embebido)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] PHI identificado (firma vincula persona con documento clinico)
- [x] Inmutabilidad legal de registros (INSERT-only)
- [x] Conforme a Ley 527/1999 Colombia (timestamp servidor, hash SHA-256, vinculacion firmante)

### Hook 4: Performance & Scalability
- [x] Response time targets definidos (< 1500ms POST con S3 upload)
- [x] Sin cache (datos legales requieren frescura)
- [x] DB indexes para queries de verificacion de unicidad
- [x] Hash calculation es O(n) en tamano del documento — aceptable para documentos clinicos

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id, document_type, document_id, signer_id incluidos)
- [x] Audit log entries definidos (create, PHI=Yes, inmutable)
- [x] Error tracking (Sentry-compatible, incluyendo hash mismatches como eventos)
- [x] Queue job monitoring (notificaciones a otras partes)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error para POST y GET)
- [x] Test data requirements specified
- [x] Mocking strategy: S3 (moto), clock (datetime mock), SVG real samples
- [x] Acceptance criteria stated con enfoque en inmutabilidad y cumplimiento legal

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
