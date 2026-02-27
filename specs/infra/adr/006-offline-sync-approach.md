# ADR-006: Offline Sync Approach

## Status
**Accepted** — February 2026

## Context
DentalOS serves dental clinics in LATAM where internet connectivity can be unreliable, particularly in rural areas of Colombia. Clinics need to continue operating during short connectivity interruptions (minutes to low hours) without losing clinical data.

We evaluated three approaches:
1. **Full offline-first with IndexedDB** — Complete local database with bidirectional sync
2. **Service Worker cache-only** — Cache static assets and recent API responses
3. **Hybrid: Service Worker + targeted IndexedDB** — Cache assets + queue critical writes

## Decision
**Deferred to post-MVP.** For MVP, we implement only:
- PWA manifest and service worker for static asset caching (I-19)
- Network-first strategy for API calls with offline fallback page
- No offline data writes or sync queue

Post-MVP (M9+), we will implement the **Hybrid approach (Option 3)**:
- IndexedDB for queuing critical writes (clinical records, odontogram changes)
- Background Sync API for replaying queued writes when connectivity returns
- Conflict resolution: last-write-wins with server timestamp, manual merge UI for clinical data conflicts
- Sync status indicator in the UI (connected/syncing/offline/conflict)

## Rationale

### Why defer?
1. **Complexity vs. timeline**: Bidirectional sync with conflict resolution for clinical data is a 4-6 week effort minimum. MVP deadline is April 2026.
2. **Colombia connectivity**: Most target clinics in Bogotá, Medellín, and Cali have reliable fiber. Rural clinics are Phase 2 (Mexico expansion).
3. **Regulatory risk**: Offline clinical data must still comply with Resolución 1888. Premature implementation risks compliance gaps.
4. **Data integrity**: Clinical records (odontogram, diagnoses, treatment plans) require careful conflict resolution. A naive implementation risks data loss or corruption.

### Why Hybrid over Full Offline-First?
1. **Smaller attack surface**: Only critical writes are queued, reducing PHI exposure in IndexedDB.
2. **Simpler conflict resolution**: Fewer data types to merge = fewer edge cases.
3. **Progressive enhancement**: Works as enhancement over the online-first MVP rather than requiring a full rewrite.
4. **Storage limits**: IndexedDB quotas vary by browser (50MB-unlimited). Full offline-first would need careful quota management for X-rays and documents.

### Why not cache-only?
Cache-only (Option 2) doesn't solve the core problem: clinics need to *write* data during outages, not just read cached pages.

## Consequences

### Positive
- MVP ships on time without offline complexity
- PWA installation still provides fast load times and app-like experience
- Clear upgrade path to Hybrid when ready
- No premature IndexedDB schema that needs migration later

### Negative
- Clinics with unreliable internet cannot use DentalOS during outages until post-MVP
- Potential competitive disadvantage vs. desktop software that works offline
- Will need to design IndexedDB schema from scratch post-MVP (no incremental learning)

### Risks
- If rural Colombia clinics are onboarded before offline support, churn risk is high
- IndexedDB encryption (for PHI at rest) varies by browser — will need a polyfill or WebCrypto wrapper

## Implementation Plan (Post-MVP)

### Phase 1: Write Queue (M9)
- IndexedDB schema for pending writes (type, payload, timestamp, retry count)
- Background Sync registration for each queued write
- Sync status component in dashboard header
- Retry logic with exponential backoff (max 5 retries)

### Phase 2: Read Cache (M10)
- Cache active patient records in IndexedDB (last 50 accessed)
- Cache current odontogram state per patient
- Cache today's appointment list
- Stale indicator in UI when showing cached data

### Phase 3: Conflict Resolution (M10)
- Server-side: accept writes with client timestamps, detect conflicts
- Client-side: merge UI for conflicting clinical records
- Audit trail: log all conflict resolutions with both versions

## Related
- ADR-001: Schema-per-tenant isolation
- ADR-008: RabbitMQ for async workloads
- I-19: PWA configuration (service worker, manifest)
- I-18: Offline-first architecture design (deferred)
