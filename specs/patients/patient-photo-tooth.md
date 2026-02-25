# Patient Tooth Photo (P-16)

---

## Overview

**Feature:** Adjuntar fotografias intraorales a un diente especifico del odontograma del paciente con una experiencia de "2 taps" (abrir camara → tomar foto → auto-vinculada al diente activo). El sistema acepta JPEG, PNG y HEIC (con conversion automatica a JPEG), almacena en S3 con organizacion por tenant/paciente/diente, genera un thumbnail 200x200 para overlay en odontograma, y retorna URLs firmadas de acceso temporal. Incluye endpoints de subida (POST), listado (GET) y eliminacion (DELETE).

**Domain:** patients

**Priority:** High

**Dependencies:** odontogram (dientes validos por nomenclatura), patients (tabla `patients`), S3/storage (infra), I-02 (authentication-rules.md), database-architecture.md (`tooth_photos`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:**
  - POST (subir foto): doctor, assistant
  - GET (listar fotos): doctor, assistant, clinic_owner
  - DELETE (eliminar foto): doctor, clinic_owner
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** El paciente debe pertenecer al mismo tenant del usuario. Los recepcionistas no tienen acceso a fotos clinicas.

---

## Endpoints

### Subir Foto a Diente Especifico

```
POST /api/v1/patients/{patient_id}/odontogram/teeth/{tooth_number}/photos
```

### Listar Fotos de un Diente

```
GET /api/v1/patients/{patient_id}/odontogram/teeth/{tooth_number}/photos
```

### Eliminar Foto

```
DELETE /api/v1/patients/{patient_id}/odontogram/teeth/{tooth_number}/photos/{photo_id}
```

**Rate Limiting:**
- POST: 60 requests por minuto por usuario (subidas frecuentes en consulta)
- GET: Inherits global rate limit (100/min per user)
- DELETE: 30 requests por minuto por usuario

---

## Request

### Headers (POST)

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | multipart/form-data | multipart/form-data; boundary=---- |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### Headers (GET / DELETE)

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | UUID | UUID v4 valido | ID del paciente | pt_550e8400-e29b-41d4-a716-446655440000 |
| tooth_number | Yes | integer | 11-18, 21-28, 31-38, 41-48 (nomenclatura FDI) | Numero de diente segun sistema FDI | 16 |
| photo_id | Yes (DELETE) | UUID | UUID v4 valido | ID de la foto a eliminar | ph_9a1b2c3d-e4f5-6789-abcd-ef0123456789 |

### Query Parameters (solo GET)

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| page | No | integer | >= 1, default: 1 | Pagina actual | 1 |
| page_size | No | integer | 1–20, default: 20 | Registros por pagina | 20 |

### Request Body Schema (POST — multipart/form-data)

| Field | Required | Type | Constraints | Description |
|-------|----------|------|-------------|-------------|
| image | Yes | file | JPEG, PNG, HEIC; max 10MB | Archivo de imagen intraoral |
| notes | No | string | max 500 chars | Nota clinica asociada a la foto |
| taken_at | No | ISO8601 datetime | Fecha/hora de la foto si difiere del momento de subida | Timestamp de cuando se tomo la foto |

**Nota UX — "2 taps":** El cliente movil llama este endpoint inmediatamente despues de que el usuario captura la foto con la camara del dispositivo. El `tooth_number` se pasa desde el diente activo en la vista del odontograma. No requiere confirmacion adicional del usuario.

---

## Response

### Success Response — POST

**Status:** 201 Created

**Schema:**
```json
{
  "id": "UUID",
  "patient_id": "UUID",
  "tooth_number": "integer",
  "url": "string — URL firmada S3, expira en 1 hora",
  "thumbnail_url": "string — URL firmada S3 del thumbnail 200x200, expira en 1 hora",
  "original_filename": "string",
  "file_size_bytes": "integer",
  "mime_type": "image/jpeg",
  "notes": "string | null",
  "taken_at": "ISO8601",
  "uploaded_by": "UUID",
  "uploaded_at": "ISO8601"
}
```

**Example:**
```json
{
  "id": "ph_9a1b2c3d-e4f5-6789-abcd-ef0123456789",
  "patient_id": "pt_550e8400-e29b-41d4-a716-446655440000",
  "tooth_number": 16,
  "url": "https://s3.amazonaws.com/dentalos-storage/tn_7c9e/patients/pt_550e/teeth/16/9a1b2c3d-e4f5-6789-abcd-ef01.jpg?X-Amz-Signature=abc123&X-Amz-Expires=3600",
  "thumbnail_url": "https://s3.amazonaws.com/dentalos-storage/tn_7c9e/patients/pt_550e/teeth/16/thumbs/9a1b2c3d-e4f5-6789-abcd-ef01_thumb.jpg?X-Amz-Signature=xyz789&X-Amz-Expires=3600",
  "original_filename": "IMG_4521.HEIC",
  "file_size_bytes": 2456789,
  "mime_type": "image/jpeg",
  "notes": "Caries incipiente en cara oclusal.",
  "taken_at": "2026-02-24T11:15:00Z",
  "uploaded_at": "2026-02-24T11:15:32Z",
  "uploaded_by": "usr_550e8400-e29b-41d4-a716-446655440000"
}
```

### Success Response — GET (Listado de fotos del diente)

**Status:** 200 OK

**Schema:**
```json
{
  "data": [
    {
      "id": "UUID",
      "tooth_number": "integer",
      "url": "string — URL firmada, 1h expiry",
      "thumbnail_url": "string — URL firmada, 1h expiry",
      "original_filename": "string",
      "file_size_bytes": "integer",
      "notes": "string | null",
      "taken_at": "ISO8601",
      "uploaded_by": "UUID",
      "uploaded_at": "ISO8601"
    }
  ],
  "pagination": {
    "page": "integer",
    "page_size": "integer",
    "total": "integer",
    "total_pages": "integer"
  }
}
```

### Success Response — DELETE

**Status:** 204 No Content

### Error Responses

#### 400 Bad Request
**When:** Formato de archivo no soportado, archivo excede 10MB, `tooth_number` fuera de rango FDI valido.

**Example:**
```json
{
  "error": "invalid_file",
  "message": "El formato del archivo no es valido. Se aceptan: JPEG, PNG, HEIC.",
  "details": {
    "image": ["Formato no soportado: GIF."]
  }
}
```

```json
{
  "error": "file_too_large",
  "message": "La imagen supera el tamano maximo permitido de 10 MB.",
  "details": {
    "image": ["Tamano recibido: 12.3 MB. Maximo permitido: 10 MB."]
  }
}
```

```json
{
  "error": "invalid_tooth_number",
  "message": "El numero de diente '99' no es valido segun la nomenclatura FDI.",
  "details": {
    "tooth_number": ["Valores validos: 11-18, 21-28, 31-38, 41-48."]
  }
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol no autorizado para la operacion, o paciente de otro tenant.

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para acceder a las fotos clinicas de este paciente."
}
```

#### 404 Not Found
**When:** `patient_id` no existe en el tenant, o `photo_id` no existe para ese diente/paciente.

```json
{
  "error": "photo_not_found",
  "message": "La foto no fue encontrada."
}
```

#### 409 Conflict
**When:** El diente ya tiene 20 fotos (limite maximo).

```json
{
  "error": "photo_limit_reached",
  "message": "El diente 16 ya tiene 20 fotografias almacenadas. Elimine alguna antes de agregar mas.",
  "details": {
    "tooth_number": 16,
    "current_count": 20,
    "max_allowed": 20
  }
}
```

#### 422 Unprocessable Entity
**When:** Error al procesar/convertir la imagen (archivo corrupto, HEIC no decodificable).

```json
{
  "error": "image_processing_failed",
  "message": "No se pudo procesar la imagen. Verifique que el archivo no este corrupto."
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error en S3 upload, falla en generacion de thumbnail.

---

## Business Logic

**Step-by-step process (POST — subir foto):**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `doctor` o `assistant`. Si no, 403.
3. Validar `tooth_number`: debe estar en el rango FDI valido (11-18, 21-28, 31-38, 41-48). Si no, 400.
4. Verificar que el paciente existe y pertenece al tenant. Si no, 404.
5. Recibir archivo multipart. Validar:
   a. MIME type detectado (no confiar en extension): `image/jpeg`, `image/png`, `image/heic`. Si no, 400.
   b. Tamano <= 10MB. Si no, 400.
6. Verificar que el diente no supera 20 fotos: `SELECT COUNT(*) FROM tooth_photos WHERE patient_id = :patient_id AND tooth_number = :tooth_number`. Si >= 20, 409.
7. **Conversion de formato:**
   - Si HEIC: convertir a JPEG usando libreria `pillow-heif` o equivalente. Si conversion falla (archivo corrupto), 422.
   - Si PNG: convertir a JPEG con calidad 90%.
   - Si JPEG: mantener como esta (recomprimir a calidad 90% si supera 8MB).
8. **Generar UUID** para la foto: `photo_uuid = uuid4()`.
9. **Path en S3:** `{tenant_id}/patients/{patient_id}/teeth/{tooth_number}/{photo_uuid}.jpg`
10. **Generar thumbnail:**
    - Redimensionar a 200x200px con crop centrado (no distorsionar).
    - Path thumbnail: `{tenant_id}/patients/{patient_id}/teeth/{tooth_number}/thumbs/{photo_uuid}_thumb.jpg`
11. **Subir ambos archivos a S3** (imagen procesada + thumbnail). Si falla el upload, retornar 500.
12. **Generar URLs firmadas** con expiracion de 1 hora para imagen y thumbnail.
13. Insertar registro en `tooth_photos` con: `patient_id`, `tooth_number`, `s3_key` (path imagen), `thumbnail_s3_key`, `file_size_bytes` (del archivo procesado), `original_filename`, `mime_type: "image/jpeg"`, `notes`, `taken_at`, `uploaded_by`.
14. Registrar en audit log: `patients.tooth_photo.uploaded` (PHI).
15. Retornar 201 Created con datos de la foto y URLs firmadas.

**Step-by-step process (GET — listar fotos):**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar rol `doctor`, `assistant` o `clinic_owner`. Si no, 403.
3. Validar `tooth_number` en rango FDI. Si no, 400.
4. Verificar que el paciente existe y pertenece al tenant. Si no, 404.
5. Consultar `tooth_photos` con paginacion, ordenado por `taken_at DESC`.
6. Para cada foto, generar URL firmada de S3 con expiracion 1 hora (imagen + thumbnail).
7. Retornar 200 con lista paginada.

**Step-by-step process (DELETE — eliminar foto):**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `doctor` o `clinic_owner`. Si no, 403 (asistentes no pueden eliminar).
3. Validar `tooth_number` y `photo_id`.
4. Verificar que la foto existe, pertenece al paciente y al tenant. Si no, 404.
5. Eliminar archivos de S3: imagen principal y thumbnail.
6. Eliminar registro de `tooth_photos`.
7. Registrar en audit log: `patients.tooth_photo.deleted` (PHI).
8. Retornar 204 No Content.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| tooth_number | Integer en rangos FDI: 11-18, 21-28, 31-38, 41-48 | "El numero de diente no es valido segun la nomenclatura FDI." |
| image | MIME: image/jpeg, image/png, image/heic | "Formato no soportado. Se aceptan: JPEG, PNG, HEIC." |
| image | Tamano <= 10MB (10,485,760 bytes) | "La imagen supera el tamano maximo de 10 MB." |
| foto count | MAX 20 fotos por diente por paciente | "El diente ya tiene el maximo de 20 fotografias." |
| notes | Max 500 chars | "Las notas no pueden superar los 500 caracteres." |

**Business Rules:**

- Las URLs de S3 siempre se sirven como URLs firmadas con expiracion de 1 hora. Nunca se exponen buckets o paths directos.
- La conversion a JPEG es siempre transparente para el usuario: la `original_filename` conserva el nombre original (ej. `IMG_4521.HEIC`), pero el archivo almacenado es JPEG.
- El path de S3 incluye el `tenant_id` como primer segmento para garantizar aislamiento de datos entre tenants.
- Fotos ordenadas por `taken_at DESC` en el listado (la mas reciente primero).
- La eliminacion de una foto borra tanto el archivo original procesado como el thumbnail de S3.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Diente 19 (diente de juicio, no en FDI estandar) | 400: fuera del rango FDI valido |
| HEIC de iOS corrupto | 422: image_processing_failed |
| Foto de 10MB exactos | Valido (limite es <= 10MB) |
| Subir foto a diente con 19 fotos | 201 OK |
| Subir foto a diente con 20 fotos | 409 Conflict |
| S3 upload falla a mitad (imagen subida, thumbnail no) | Rollback: eliminar imagen de S3 si fue subida, no insertar DB, retornar 500 |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `tooth_photos`: INSERT (POST), DELETE (DELETE) — registro de foto con metadatos y paths S3

**Example query (SQLAlchemy):**
```python
from sqlalchemy import insert, select, func

# Verificar limite antes de subir
count_result = await session.execute(
    select(func.count(ToothPhoto.id))
    .where(
        ToothPhoto.patient_id == patient_id,
        ToothPhoto.tooth_number == tooth_number,
        ToothPhoto.tenant_id == tenant_id,
    )
)
current_count = count_result.scalar_one()
if current_count >= 20:
    raise PhotoLimitReachedException(tooth_number=tooth_number)

# Insertar foto tras upload exitoso
await session.execute(
    insert(ToothPhoto).values(
        id=photo_uuid,
        patient_id=patient_id,
        tenant_id=tenant_id,
        tooth_number=tooth_number,
        s3_key=s3_image_path,
        thumbnail_s3_key=s3_thumbnail_path,
        file_size_bytes=processed_file_size,
        original_filename=upload.filename,
        mime_type="image/jpeg",
        notes=body.notes,
        taken_at=body.taken_at or datetime.utcnow(),
        uploaded_by=user_id,
    )
)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:tooth:{tooth_number}:photos`: DELETE (invalidacion al subir o eliminar foto)

**Cache TTL:** N/A (invalidacion al escribir)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno — la conversion y generacion de thumbnail ocurren sincronamente antes de subir a S3.

### Audit Log

**Audit entry:** Yes

- **Action:** create (POST), read (GET), delete (DELETE)
- **Resource:** tooth_photo
- **PHI involved:** Yes (fotos intraorales son imagenes de salud del paciente)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target (POST):** < 2000ms (incluye conversion de imagen, upload S3 de 2 archivos, insert DB)
- **Maximum acceptable (POST):** < 5000ms (imagen HEIC grande de 10MB)
- **Target (GET):** < 300ms (listado con URLs firmadas)
- **Target (DELETE):** < 500ms (delete S3 + DB)

### Caching Strategy
- **Strategy:** Sin cache para el listado en Redis (URLs firmadas expiran, cache seria invalido en 1h). Las URLs firmadas se generan en cada request.
- **Cache key:** N/A para fotos
- **TTL:** URLs firmadas S3: 3600s (1 hora)
- **Invalidation:** N/A

### Database Performance

**Queries executed (POST):** 3 (verificar paciente, COUNT fotos del diente, INSERT foto)

**Indexes required:**
- `tooth_photos.patient_id` — INDEX
- `tooth_photos.(patient_id, tooth_number)` — INDEX COMPUESTO (para COUNT de limite)
- `tooth_photos.tenant_id` — INDEX
- `tooth_photos.taken_at` — INDEX (para ordenamiento)

**N+1 prevention:** Listado con paginacion simple, no hay objetos anidados que requieran joins adicionales.

### Pagination

**Pagination:** Yes (GET)

- **Style:** offset-based
- **Default page size:** 20
- **Max page size:** 20 (maximo igual al limite de fotos por diente)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id, photo_id (URL) | Pydantic UUID | |
| tooth_number (URL) | Pydantic int, validacion enum FDI | |
| image (file) | MIME detection en servidor (no confiar en Content-Type del cliente) | Usar `python-magic` para deteccion real |
| notes | Pydantic str, strip, max_length=500, bleach | |
| taken_at | Pydantic datetime | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Campos string sanitizados con bleach. URLs de S3 son generadas por AWS SDK (no interpoladas).

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Las fotografias intraorales son imagenes de salud del paciente — clasificadas como PHI. El campo `notes` puede contener observaciones clinicas.

**Audit requirement:** All access logged — subida, listado y eliminacion auditados por contener PHI (imagenes clinicas).

**S3 Security:**
- Bucket configurado como **privado** (no publico).
- Acceso exclusivo via URLs pre-firmadas con expiracion de 1 hora.
- IAM role del servidor con permisos minimos (s3:PutObject, s3:GetObject, s3:DeleteObject) solo en el bucket de DentalOS.
- Paths de S3 incluyen `tenant_id` como primer segmento para particionamiento de datos.

---

## Testing

### Test Cases

#### Happy Path
1. Subir foto JPEG valida a diente 16
   - **Given:** Paciente activo, usuario `doctor`, diente 16 sin fotos, archivo JPEG 2MB
   - **When:** POST /api/v1/patients/{id}/odontogram/teeth/16/photos con imagen JPEG
   - **Then:** 201 Created, `url` y `thumbnail_url` son URLs firmadas S3, `mime_type: "image/jpeg"`, registro en DB

2. Subir foto HEIC (conversion automatica)
   - **Given:** Archivo HEIC de 5MB
   - **When:** POST con archivo HEIC
   - **Then:** 201 Created, `original_filename` termina en `.HEIC`, `mime_type: "image/jpeg"`, archivo en S3 es JPEG

3. Subir foto PNG (conversion automatica)
   - **Given:** Archivo PNG de 3MB
   - **When:** POST con archivo PNG
   - **Then:** 201 Created, archivo almacenado como JPEG

4. Listar fotos del diente (GET)
   - **Given:** Diente 16 con 3 fotos, usuario `doctor`
   - **When:** GET /api/v1/patients/{id}/odontogram/teeth/16/photos
   - **Then:** 200 OK, `total: 3`, URLs firmadas vigentes, ordenadas por `taken_at DESC`

5. Eliminar foto (DELETE)
   - **Given:** Foto existente, usuario `clinic_owner`
   - **When:** DELETE /api/v1/patients/{id}/odontogram/teeth/16/photos/{photo_id}
   - **Then:** 204 No Content, foto eliminada de S3 (imagen + thumbnail) y de DB

6. Assistant puede subir fotos
   - **Given:** Usuario con rol `assistant`
   - **When:** POST foto
   - **Then:** 201 Created

#### Edge Cases
1. Diente con 19 fotos (penultima permitida)
   - **Given:** Diente 16 con exactamente 19 fotos
   - **When:** POST nueva foto
   - **Then:** 201 Created (se llega a 20, que es el limite)

2. S3 falla al subir thumbnail (imagen ya subida)
   - **Given:** Upload de imagen exitoso, upload de thumbnail falla
   - **When:** POST foto
   - **Then:** 500, imagen de S3 eliminada en rollback, no hay registro en DB

3. Foto con nota y taken_at explicitos
   - **Given:** App movil envia timestamp de cuando se tomo la foto
   - **When:** POST con `notes` y `taken_at`
   - **Then:** 201, `notes` y `taken_at` guardados correctamente

#### Error Cases
1. Diente numero invalido (fuera de FDI)
   - **Given:** `tooth_number = 55`
   - **When:** POST /teeth/55/photos
   - **Then:** 400 Bad Request con mensaje de valores validos

2. Archivo GIF (formato no soportado)
   - **Given:** Archivo GIF enviado
   - **When:** POST
   - **Then:** 400 Bad Request con formatos aceptados

3. Archivo mayor a 10MB
   - **Given:** Archivo JPEG de 11MB
   - **When:** POST
   - **Then:** 400 con tamano recibido y maximo permitido

4. Diente con 20 fotos (limite alcanzado)
   - **Given:** Diente 16 con 20 fotos
   - **When:** POST foto numero 21
   - **Then:** 409 Conflict con `current_count: 20` y `max_allowed: 20`

5. Eliminar foto con rol assistant (no permitido)
   - **Given:** Usuario con rol `assistant`
   - **When:** DELETE /teeth/16/photos/{id}
   - **Then:** 403 Forbidden

6. Foto de paciente de otro tenant
   - **Given:** `patient_id` de tenant B, usuario en tenant A
   - **When:** POST o GET
   - **Then:** 404 Not Found

7. HEIC corrupto
   - **Given:** Archivo con extension HEIC pero datos corruptos
   - **When:** POST
   - **Then:** 422 Unprocessable Entity — image_processing_failed

### Test Data Requirements

**Users:** Un `doctor`, un `assistant`, un `clinic_owner`, un `receptionist` (para test 403).

**Patients:** Un paciente activo del tenant A, un paciente del tenant B.

**Fotos seed:** Diente 16 con 19 fotos (para test de limite), diente 21 con 0 fotos, diente 32 con 1 foto (para test de DELETE).

**Archivos de prueba:** JPEG valido (2MB), PNG valido (3MB), HEIC valido (5MB), GIF invalido, JPEG > 10MB, HEIC corrupto.

### Mocking Strategy

- **S3 (AWS):** moto o localstack para simular upload/delete en tests de integracion. Mock simple en unit tests.
- **HEIC converter:** Mock de `pillow-heif` para unit tests. Test real en integration tests con archivo HEIC valido.
- **python-magic:** Mock para controlar MIME detection en tests de formato invalido.
- **Redis:** fakeredis para rate limiting.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST sube imagen, genera thumbnail 200x200, almacena en S3, retorna 201 con URLs firmadas (1h expiry)
- [ ] HEIC y PNG se convierten automaticamente a JPEG antes de subir
- [ ] `original_filename` preserva nombre original del archivo
- [ ] Limite de 20 fotos por diente se valida con 409
- [ ] `tooth_number` fuera de rango FDI retorna 400
- [ ] Archivo > 10MB retorna 400 con tamano recibido
- [ ] GET lista fotos ordenadas por `taken_at DESC` con URLs firmadas
- [ ] DELETE elimina imagen y thumbnail de S3 y registro de DB
- [ ] `assistant` puede subir pero no eliminar (403 en DELETE)
- [ ] Paciente de otro tenant retorna 404
- [ ] PHI auditado (subida, listado y eliminacion en audit log)
- [ ] S3 paths incluyen `tenant_id` como primer segmento
- [ ] All test cases pass
- [ ] Performance targets met (< 5000ms POST con HEIC 10MB)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Anotaciones o markup sobre las fotos (flechas, texto)
- Comparacion before/after de fotos del mismo diente
- Generacion de reportes con fotos incluidas
- Fotos adjuntas a historia clinica general (no a diente especifico)
- Video intraoral
- Integracion con camara intraoral inalambrica (bluetooth — post-MVP)
- Compresion progresiva o formatos WebP

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (multipart/form-data schema + URL params para los 3 endpoints)
- [x] All outputs defined (response models para POST, GET, DELETE)
- [x] API contract defined (OpenAPI compatible, 3 endpoints documentados)
- [x] Validation rules stated (FDI, tamano, formato, limite fotos)
- [x] Error cases enumerated (formato invalido, tamano, limite, S3 fallo, formato corrupto)
- [x] Auth requirements explicit (doctor/assistant POST, doctor/owner DELETE)
- [x] Side effects listed (S3 upload, DB insert, audit log PHI)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (patients domain, odontogram sub-resource)
- [x] Uses tenant schema isolation (tenant_id en S3 path y DB)
- [x] Matches FastAPI conventions (async, dependency injection, UploadFile)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role diferenciado por operacion)
- [x] Input sanitization definida (MIME detection real con python-magic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] PHI identificado (fotos intraorales) y auditado en todas las operaciones
- [x] S3 privado con pre-signed URLs (nunca paths directos)
- [x] Tenant isolation en S3 path

### Hook 4: Performance & Scalability
- [x] Response time targets definidos por operacion
- [x] Thumbnail generado sincronamente (necesario para respuesta inmediata)
- [x] Sin cache para listado (URLs firmadas tienen TTL corto)
- [x] DB indexes listados para queries de COUNT y listado

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id, patient_id, tooth_number incluidos)
- [x] Audit log entries definidos (create/read/delete, PHI=Yes)
- [x] Error tracking (Sentry-compatible, incluyendo errores S3)
- [x] Queue job monitoring (N/A)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error para los 3 endpoints)
- [x] Test data requirements specified (archivos de prueba listados)
- [x] Mocking strategy para S3 (moto/localstack), HEIC converter, python-magic
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
