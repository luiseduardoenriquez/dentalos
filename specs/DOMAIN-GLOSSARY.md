# DentalOS -- Domain Glossary

> Bilingual glossary of dental, regulatory, and technical terms used across all DentalOS specifications.
> **Convention:** Spanish term first (as used in the codebase and UI), followed by English explanation.

**Version:** 1.0
**Date:** 2026-02-24
**Audience:** All developers, designers, and stakeholders working on DentalOS

---

## 1. Dental Anatomy and Terminology

### 1.1 Odontograma (Dental Chart)

A visual diagram representing the condition of every tooth in a patient's mouth. DentalOS supports two rendering modes:

- **Classic mode:** Grid-based layout with tooth icons arranged in rows
- **Anatomic mode:** Arch-shaped layout mimicking the natural jaw curvature

Each tooth is represented as an interactive SVG element. Clicking a tooth opens its detail panel where conditions, treatments, and notes can be recorded.

### 1.2 Nomenclatura FDI (FDI Tooth Numbering System)

The **Federation Dentaire Internationale** (FDI World Dental Federation) two-digit numbering system, universally used in LATAM clinical practice. DentalOS uses FDI as its primary tooth identification system.

**Structure:** `[quadrant digit][tooth position digit]`

**Adult Dentition (32 teeth):**

| Quadrant | Number | Location | Teeth Range |
|----------|--------|----------|-------------|
| 1 | Upper Right | Maxillary right | 11-18 |
| 2 | Upper Left | Maxillary left | 21-28 |
| 3 | Lower Left | Mandibular left | 31-38 |
| 4 | Lower Right | Mandibular right | 41-48 |

**Tooth positions within each quadrant:**

| Position | Tooth Type (Spanish) | Tooth Type (English) |
|----------|---------------------|---------------------|
| 1 | Incisivo central | Central incisor |
| 2 | Incisivo lateral | Lateral incisor |
| 3 | Canino | Canine |
| 4 | Primer premolar | First premolar |
| 5 | Segundo premolar | Second premolar |
| 6 | Primer molar | First molar |
| 7 | Segundo molar | Second molar |
| 8 | Tercer molar (muela del juicio) | Third molar (wisdom tooth) |

**Examples:**
- `11` = Upper right central incisor
- `36` = Lower left first molar
- `48` = Lower right third molar (wisdom tooth)

**Pediatric Dentition (20 teeth):**

| Quadrant | Number | Location | Teeth Range |
|----------|--------|----------|-------------|
| 5 | Upper Right | Maxillary right | 51-55 |
| 6 | Upper Left | Maxillary left | 61-65 |
| 7 | Lower Left | Mandibular left | 71-75 |
| 8 | Lower Right | Mandibular right | 81-85 |

Pediatric teeth use positions 1-5 only (no premolars or third molars).

### 1.3 Tipos de Dientes (Types of Teeth)

| Spanish | English | Count (Adult) | Position per Arch |
|---------|---------|---------------|-------------------|
| Incisivo | Incisor | 8 (4 upper, 4 lower) | Central and lateral, front of mouth |
| Canino | Canine | 4 (2 upper, 2 lower) | Corner teeth, one per quadrant |
| Premolar | Premolar | 8 (4 upper, 4 lower) | Behind canines, two per quadrant |
| Molar | Molar | 12 (6 upper, 6 lower) | Back of mouth, three per quadrant (including wisdom) |

**Total adult teeth:** 32
**Total pediatric teeth:** 20 (no premolars, only two molars per quadrant)

### 1.4 Superficies Dentales (Tooth Surfaces)

Each crown has 5 surfaces that can be independently affected by conditions or treatments:

| Code | Spanish | English | Location |
|------|---------|---------|----------|
| O | Oclusal | Occlusal | Top/biting surface (only on premolars and molars) |
| M | Mesial | Mesial | Surface facing toward the midline of the dental arch |
| D | Distal | Distal | Surface facing away from the midline |
| V | Vestibular (Bucal) | Buccal/Labial | Surface facing the cheek or lip |
| L/P | Lingual / Palatino | Lingual / Palatal | Surface facing the tongue (lower) or palate (upper) |

**Note:** Incisors and canines use **Incisal** (I) instead of Oclusal (O) for their biting edge. In the DentalOS data model, this is normalized to `O` for simplicity but displayed correctly in the UI.

### 1.5 Raiz (Root)

The sub-gingival (below the gum line) structure of the tooth. Root-level conditions tracked in DentalOS include:

- **Endodoncia** (root canal treatment)
- **Fractura radicular** (root fracture)
- **Reabsorcion** (root resorption)

Root information is recorded separately from crown surfaces in the odontogram data model.

### 1.6 Condiciones Clinicas (Clinical Conditions)

The 12 clinical conditions tracked per tooth/surface in the DentalOS odontogram:

| Code | Spanish | English | Description | Visual |
|------|---------|---------|-------------|--------|
| SAN | Sano | Healthy | No pathology or treatment | No marking |
| CAR | Caries | Cavity/Decay | Active tooth decay | Red fill on affected surface |
| RES | Resina | Composite resin | Tooth-colored filling | Blue fill on affected surface |
| AMA | Amalgama | Amalgam | Silver/metal filling | Gray fill on affected surface |
| COR | Corona | Crown | Full coverage crown | Circle around tooth |
| AUS | Ausente | Missing | Tooth not present | X mark through tooth |
| IMP | Implante | Implant | Dental implant placed | Triangle below tooth |
| END | Endodoncia | Root canal | Root canal treatment | Line through root |
| SEL | Sellante | Sealant | Preventive pit/fissure sealant | Green fill on occlusal |
| FRA | Fractura | Fracture | Tooth fracture | Zigzag line |
| CPR | Caries Profunda | Deep cavity | Cavity near pulp chamber | Dark red fill |
| ABR | Abrasion | Abrasion | Wear of tooth surface | Hatched marking |

### 1.7 Denticion Mixta (Mixed Dentition)

The transitional period in children (approximately ages 6-12) where both primary (deciduous/baby) and permanent teeth are present simultaneously. DentalOS handles this by allowing a patient's odontogram to contain teeth from both the pediatric (quadrants 5-8) and adult (quadrants 1-4) numbering systems at the same time.

### 1.8 Periodontograma (Periodontal Chart)

A specialized chart recording periodontal (gum) health measurements including pocket depth, recession, bleeding on probing, and mobility. **Post-MVP feature** -- not included in the initial release.

### 1.9 Anamnesis (Medical History)

The structured questionnaire capturing a patient's complete medical history, including:

- Antecedentes personales (personal medical history)
- Antecedentes familiares (family medical history)
- Alergias (allergies, especially to anesthetics and medications)
- Medicamentos actuales (current medications)
- Enfermedades sistemicas (systemic diseases: diabetes, hypertension, cardiac conditions)
- Habitos (habits: smoking, bruxism, etc.)
- Embarazo (pregnancy status)

Anamnesis is recorded as part of the clinical record and reviewed at each visit.

---

## 2. Classification and Coding Systems

### 2.1 CIE-10 / ICD-10 (International Classification of Diseases, 10th Revision)

**Spanish:** Clasificacion Internacional de Enfermedades, Decima Revision
**English:** International Classification of Diseases, 10th Revision

Standardized diagnostic codes used to classify dental conditions. DentalOS uses the dental-relevant subset:

| Range | Category |
|-------|----------|
| K00-K14 | Diseases of oral cavity, salivary glands and jaws |
| K00 | Disorders of tooth development and eruption |
| K01 | Embedded and impacted teeth |
| K02 | Dental caries |
| K03 | Other diseases of hard tissues of teeth |
| K04 | Diseases of pulp and periapical tissues |
| K05 | Gingivitis and periodontal diseases |
| K06 | Other disorders of gingiva and edentulous alveolar ridge |
| K07 | Dentofacial anomalies |
| K08 | Other disorders of teeth and supporting structures |
| K09-K14 | Cysts, other jaw/oral diseases |
| S02.5 | Fracture of tooth |

DentalOS provides a searchable CIE-10 catalog endpoint: `GET /api/v1/catalog/cie10`

### 2.2 CUPS (Clasificacion Unica de Procedimientos en Salud)

**Spanish:** Clasificacion Unica de Procedimientos en Salud
**English:** Unified Health Procedures Classification (Colombia-specific)

Standardized procedure codes used in Colombia for billing and reporting dental procedures. Each dental treatment in DentalOS maps to one or more CUPS codes.

**Common dental CUPS codes:**

| Code | Procedure |
|------|-----------|
| 232101 | Obturacion dental con amalgama |
| 232102 | Obturacion dental con resina |
| 232201 | Endodoncia unirradicular |
| 232301 | Exodoncia simple |
| 232401 | Profilaxis dental |
| 237101 | Corona individual |

DentalOS provides a searchable CUPS catalog endpoint: `GET /api/v1/catalog/cups`

**Note:** Other LATAM countries use their own procedure classification systems. The compliance adapter pattern (see ADR-007) abstracts this per country.

---

## 3. Regulatory and Compliance Terms

### 3.1 Colombia

| Term | Full Name | Description |
|------|-----------|-------------|
| **RDA** | Registro Dental Automatizado | Colombia's dental records regulation (Resolucion 1888 de 2025). Mandates electronic dental records including odontogram format, required data fields, and retention policies. DentalOS targets full RDA compliance. |
| **RIPS** | Registro Individual de Prestacion de Servicios de Salud | Colombia's mandatory health service reporting format. Dental practices must submit RIPS files to EPS (insurance entities) for payment processing. |
| **EPS** | Entidad Promotora de Salud | Health insurance entities in Colombia. Patients may be covered by an EPS, affecting billing flows and RIPS generation. |
| **DIAN** | Direccion de Impuestos y Aduanas Nacionales | Colombia's tax authority. Requires electronic invoicing (facturacion electronica) for all businesses. DentalOS integrates with DIAN for invoice validation. |

**RIPS File Types:**

| File Code | Name | Contents |
|-----------|------|----------|
| AF | Archivo de transacciones | Transaction file (header) |
| AC | Archivo de consultas | Consultation records |
| AP | Archivo de procedimientos | Procedure records |
| AT | Archivo de otros servicios | Other services |
| AM | Archivo de medicamentos | Medication records |
| AN | Archivo de recien nacidos | Newborn records (not dental-relevant) |
| AU | Archivo de urgencias | Emergency records |

### 3.2 Mexico

| Term | Full Name | Description |
|------|-----------|-------------|
| **SAT** | Servicio de Administracion Tributaria | Mexico's tax authority. Requires CFDI (Comprobante Fiscal Digital por Internet) for all invoices. |
| **CFDI** | Comprobante Fiscal Digital por Internet | Mexico's electronic invoice format. DentalOS generates CFDI-compliant invoices for Mexican tenants. |
| **NOM-024** | Norma Oficial Mexicana NOM-024-SSA3 | Mexican regulation for electronic health records. Defines minimum data requirements, interoperability standards, and security controls for clinical systems. |

### 3.3 Chile

| Term | Full Name | Description |
|------|-----------|-------------|
| **SII** | Servicio de Impuestos Internos | Chile's tax authority. Requires DTE (Documento Tributario Electronico) for electronic invoicing. |
| **DTE** | Documento Tributario Electronico | Chile's electronic tax document format. |

### 3.4 Peru

| Term | Full Name | Description |
|------|-----------|-------------|
| **RENHICE** | Registro Nacional de Historias Clinicas Electronicas | Peru's national registry for electronic health records. Defines standards for clinical data storage and exchange. |

### 3.5 Cross-Country

| Term | Full Name | Description |
|------|-----------|-------------|
| **PHI** | Protected Health Information | Any individually identifiable health information. DentalOS treats all clinical data (odontograms, diagnoses, treatments, medical history) as PHI. Access is audit-logged, encrypted at rest and in transit. |

---

## 4. Technical and Platform Terms

### 4.1 Architecture

| Term | Definition |
|------|-----------|
| **Tenant** | An individual dental practice or clinic registered in DentalOS. Each tenant has completely isolated data. A tenant may represent a single-dentist practice or a multi-location clinic group. |
| **Schema-per-tenant** | The PostgreSQL multi-tenancy strategy used by DentalOS. Each tenant gets its own PostgreSQL schema (e.g., `tenant_abc123`), providing strong data isolation without requiring separate database instances. See ADR-001. |
| **Multi-tenant** | A single application instance serving multiple clinics simultaneously. All tenants share the same application code and infrastructure, but data is strictly isolated per tenant. |
| **Tenant slug** | A URL-friendly identifier for the tenant, used in public-facing URLs (e.g., `clinica-dental-sonrisa`). Immutable after creation. |
| **Tenant resolution** | The process of identifying which tenant a request belongs to. In DentalOS, resolved from the JWT token's `tenant_id` claim for authenticated requests, or from the URL path for public endpoints. |
| **Shared schema** | The PostgreSQL `public` schema containing cross-tenant data: tenant registry, subscription plans, superadmin accounts, CIE-10 catalog, CUPS catalog. |

### 4.2 Authentication and Authorization

| Term | Definition |
|------|-----------|
| **RBAC** | Role-Based Access Control. DentalOS defines six roles with hierarchical permissions. |
| **JWT** | JSON Web Token. The stateless authentication mechanism used by DentalOS. Access tokens (15-minute TTL) contain user ID, tenant ID, and role. |
| **Access token** | Short-lived JWT (15 min) used to authenticate API requests. Sent in the `Authorization: Bearer` header. |
| **Refresh token** | Long-lived token (30 days) used to obtain new access tokens without re-authentication. Single-use with replay detection. |
| **Superadmin** | Platform-level administrator (DentalOS team). Can manage all tenants, view platform metrics, suspend accounts. Not associated with any specific tenant. |

**RBAC Roles (ordered by privilege level):**

| Role | Spanish | Scope | Description |
|------|---------|-------|-------------|
| `superadmin` | Superadministrador | Platform | DentalOS platform administration |
| `clinic_owner` | Dueno de clinica | Tenant | Full control over clinic settings, users, billing |
| `doctor` | Doctor/Odontologo | Tenant | Clinical access: patients, odontograms, records, treatments |
| `assistant` | Asistente | Tenant | Supports doctor: patient records, notes, limited clinical access |
| `receptionist` | Recepcionista | Tenant | Front desk: appointments, patient registration, basic billing |
| `patient` | Paciente | Self | Portal access: own appointments, records, consents |

### 4.3 Frontend

| Term | Definition |
|------|-----------|
| **PWA** | Progressive Web App. DentalOS is built as a PWA to support offline use, installation on devices, and push notifications -- critical for LATAM clinics with unreliable internet. |
| **Odontogram mode** | The visual rendering style for the dental chart. **Classic** shows a grid layout. **Anatomic** shows a realistic arch. Configurable per tenant. |
| **Service Worker** | Browser-level script that intercepts network requests, enabling offline caching and background sync. |
| **IndexedDB** | Browser-based database used for offline data storage. DentalOS stores pending clinical changes in IndexedDB when offline and syncs when connectivity returns. |

### 4.4 Infrastructure

| Term | Definition |
|------|-----------|
| **RabbitMQ** | Message broker used for asynchronous task processing. Handles email delivery, WhatsApp notifications, RIPS generation, invoice creation, and audit log writes. See ADR-008. |
| **Redis** | In-memory data store used for caching (session data, plan limits, odontogram state, appointment slots), rate limiting, and real-time features. |
| **Alembic** | Database migration tool for SQLAlchemy. DentalOS runs migrations per-tenant across all schemas. |
| **pgbouncer** | PostgreSQL connection pooler. Required for schema-per-tenant to avoid connection exhaustion. |
| **DLQ** | Dead Letter Queue. RabbitMQ queue where failed messages are sent after exhausting retry attempts. Monitored for alerting. |

---

## 5. Business and Billing Terms

| Term | Spanish | Definition |
|------|---------|-----------|
| **Plan** | Plan | Subscription tier for a tenant. Defines limits on doctors, patients, storage, and features. |
| **Factura electronica** | Electronic invoice | Legally valid digital invoice, required in all target LATAM countries. Format varies by country (DIAN, CFDI, DTE). |
| **Presupuesto** | Treatment estimate/quote | Cost estimate presented to patient before treatment. Can be accepted, modified, or rejected. |
| **Abono** | Partial payment | Installment payment against a treatment plan balance. Common in LATAM dental practices. |
| **Consentimiento informado** | Informed consent | Legal document signed by patient before procedures. DentalOS supports digital signatures. |
| **Historia clinica** | Clinical record | The complete medical record for a patient visit, including anamnesis, examination, diagnosis (CIE-10), treatment performed (CUPS), and prescriptions. |

---

## 6. Abbreviations Quick Reference

| Abbreviation | Meaning |
|-------------|---------|
| ADR | Architecture Decision Record |
| API | Application Programming Interface |
| CFDI | Comprobante Fiscal Digital por Internet |
| CIE-10 | Clasificacion Internacional de Enfermedades, 10a Revision |
| CUPS | Clasificacion Unica de Procedimientos en Salud |
| DIAN | Direccion de Impuestos y Aduanas Nacionales |
| DLQ | Dead Letter Queue |
| DTE | Documento Tributario Electronico |
| EPS | Entidad Promotora de Salud |
| FDI | Federation Dentaire Internationale |
| JWT | JSON Web Token |
| MVP | Minimum Viable Product |
| NOM | Norma Oficial Mexicana |
| PHI | Protected Health Information |
| PWA | Progressive Web App |
| RBAC | Role-Based Access Control |
| RDA | Registro Dental Automatizado |
| RENHICE | Registro Nacional de Historias Clinicas Electronicas |
| RIPS | Registro Individual de Prestacion de Servicios de Salud |
| SAT | Servicio de Administracion Tributaria |
| SII | Servicio de Impuestos Internos |
| SVG | Scalable Vector Graphics |
| TTL | Time To Live |
| UUID | Universally Unique Identifier |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial glossary covering dental, regulatory, and technical terms |
