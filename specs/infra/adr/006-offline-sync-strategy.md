# ADR-006: Offline Sync with Service Workers + IndexedDB

**Status:** Proposed
**Date:** 2026-02-24
**Authors:** DentalOS Architecture Team

---

## Context

Many dental clinics in Latin America operate with unreliable internet connectivity. Internet outages are common in rural and semi-urban areas across Colombia, Mexico, Peru, Chile, and Argentina. A dentist mid-procedure cannot pause to wait for a network request to save a finding on the odontogram or record a clinical note. The application must continue functioning during connectivity gaps and synchronize data when the connection returns.

### Problem Statement

DentalOS is a web application (React SPA with FastAPI backend). Without an offline strategy, every user action that writes data (update odontogram, save clinical note, register a patient, create an appointment) fails silently or shows an error when the network is unavailable. This is unacceptable for clinical workflows where data loss could mean lost patient records or incomplete clinical documentation.

### Usage Scenarios

| Scenario | Frequency | Duration | Data at Risk |
|----------|-----------|----------|--------------|
| Brief internet dropout | Daily | 5-60 seconds | In-flight API requests |
| Extended outage (ISP issue) | Weekly in some regions | 5-60 minutes | Active clinical session data |
| Working in area with no connectivity | Occasional (rural clinics) | Hours | Full day of clinical work |
| Network congestion (shared connection) | Common | Intermittent | Sporadic request failures |

### Scope Delineation

- **MVP (Sprints 1-12):** Optimistic UI with automatic retry for short connectivity gaps. If a write request fails, it is retried with exponential backoff (3 attempts, 5s/15s/45s). The UI shows inline error indicators for unsynced changes. No offline data persistence -- refreshing the page during an outage loses unsaved work.
- **Post-MVP (Sprint 13+):** Full offline-first implementation as described in this ADR. Service Workers for asset caching, IndexedDB for data persistence, background sync queue, conflict resolution.

This ADR documents the target architecture for the post-MVP phase. The MVP implementation must not make decisions that would prevent this architecture from being adopted later.

### Constraints

- DentalOS is a PWA (Progressive Web App), not a native mobile app. Offline capabilities are limited to what the browser platform provides: Service Workers, IndexedDB, Cache API, Background Sync API.
- Patient data (PHI) stored in IndexedDB must be treated as sensitive. Browser storage is not encrypted at rest by default on all platforms. This is an accepted trade-off for offline functionality -- the alternative (no offline support) is worse for patient care.
- Conflict resolution must handle the case where two users at the same clinic modify the same patient's odontogram while one is offline.
- IndexedDB storage limits vary by browser (typically 50-80% of available disk space). DentalOS must monitor and manage storage usage.

---

## Decision

We will implement a PWA with Service Workers for asset caching and IndexedDB for data persistence. Clinical data writes are queued in IndexedDB when the network is unavailable and synchronized via a background sync queue when connectivity returns.

### Service Worker Strategy

The Service Worker handles two concerns:

**1. Asset Caching (Workbox with precache + runtime cache)**

- **Precache:** All static assets (JS bundles, CSS, fonts, SVG tooth paths) are precached at Service Worker install time. This ensures the application shell loads instantly, even offline.
- **Runtime cache (Stale-While-Revalidate):** API responses for read-heavy, slowly-changing data (CIE-10 catalog, CUPS catalog, tenant settings, user profile) are cached and served from cache while revalidating in the background.
- **Network-first for clinical data:** Patient records, odontogram state, appointments, and treatment plans always attempt the network first. Cache is used only as a fallback when offline.

**2. Background Sync**

When a data write fails due to network unavailability, the write payload is stored in IndexedDB and a `sync` event is registered with the Service Worker. When connectivity returns, the Service Worker triggers the sync queue processor, which replays the queued writes in order.

### IndexedDB Schema Design

```
dentalos_offline (database)
  ├── sync_queue (object store)
  │   Key: auto-increment
  │   Fields: id, url, method, body, headers, timestamp, retryCount, status
  │
  ├── odontogram_cache (object store)
  │   Key: [patientId, toothNumber]
  │   Fields: patientId, toothNumber, conditions, updatedAt, syncedAt
  │
  ├── clinical_notes_cache (object store)
  │   Key: noteId (UUID, generated client-side)
  │   Fields: noteId, patientId, content, createdAt, syncedAt
  │
  ├── patient_cache (object store)
  │   Key: patientId
  │   Fields: patientId, data (JSON), fetchedAt, syncedAt
  │
  └── metadata (object store)
      Key: key
      Fields: key, value (e.g., lastSyncTimestamp, storageUsageBytes)
```

### Sync Queue Processing

The sync queue processes entries in strict FIFO order (oldest first) to preserve causal ordering. Each entry is an API request that failed due to network unavailability.

```
Queue entry lifecycle:
  PENDING -> SYNCING -> SYNCED (removed)
                     -> FAILED (retry with backoff, max 5 attempts)
                     -> DEAD (max retries exhausted, alert user)
```

**Sync priority order:**

1. **Clinical data first:** Odontogram updates, clinical notes, diagnoses, treatment records.
2. **Patient data second:** Patient registration, profile updates.
3. **Appointment data third:** Appointment creation, modifications.
4. **Billing data last:** Invoice generation, payment records.

This ordering ensures that the most clinically important data reaches the server first when bandwidth is limited.

### Conflict Resolution

**Default strategy: Last-write-wins with server timestamp.**

For most resources (patient profiles, appointments, clinical notes), the server accepts the most recent write based on the server-assigned timestamp at the time of sync. The client includes an `If-Unmodified-Since` header (or equivalent `version` field) to detect conflicts.

**Odontogram-specific strategy: Surface-level merge.**

The odontogram is the most conflict-prone resource because multiple clinicians may examine the same patient. Conflicts are resolved at the surface level, not the whole-odontogram level:

- Each surface condition change is recorded as an individual operation with a timestamp.
- When syncing, the server compares the client's base version (the version the client last fetched) with the current server version.
- If the same surface was modified by both client and server, the server timestamp wins.
- If different surfaces were modified, both changes are merged without conflict.

This is a practical compromise. True concurrent editing of the exact same tooth surface by two different clinicians is rare (it would require two dentists examining the same patient at the same time, which is clinically unusual).

### Sync Status Indicators in UI

The UI must clearly communicate sync status at all times:

| Indicator | Location | Meaning |
|-----------|----------|---------|
| Green cloud icon | Top navbar | All data synced, online |
| Yellow cloud with arrow | Top navbar | Online, sync in progress (N pending) |
| Red cloud with X | Top navbar | Offline, changes queued locally |
| Per-field yellow dot | Next to modified fields | This specific change has not been synced yet |
| Sync progress bar | Bottom sheet (expandable) | Shows sync queue depth and progress |

### Bandwidth-Aware Sync

On slow connections (detected via `navigator.connection.effectiveType`), the sync engine:

- Reduces batch size from 10 to 3 queued requests per sync cycle.
- Skips non-critical syncs (e.g., analytics events) until connection improves.
- Compresses request payloads using `Content-Encoding: gzip` when supported.
- Prioritizes clinical data sync over all other data types.

### Data Integrity Verification

After a sync cycle completes, the client performs a lightweight verification:

1. For each synced odontogram, fetch the server's current state and compare checksums.
2. If a discrepancy is detected, fetch the full resource and update the local cache.
3. Log discrepancies as sync audit events for debugging.

---

## Alternatives Considered

### Alternative 1: Optimistic UI with Retry Only (No Offline Persistence)

Use optimistic UI updates with automatic retry (exponential backoff) for failed requests. No local data persistence -- if the user refreshes the page during an outage, unsaved changes are lost.

**Why rejected for post-MVP:**

- Acceptable for the MVP phase (short connectivity gaps of seconds).
- Unacceptable for extended outages (minutes to hours). A dentist who has been charting for 30 minutes would lose all work if the browser tab is closed or refreshed during an outage.
- Does not support the "rural clinic with no internet" scenario at all.

**Trade-offs:** Simplest to implement. Zero conflict resolution complexity. But fundamentally limited by the lack of persistence.

### Alternative 2: CouchDB/PouchDB Sync

Use PouchDB as the client-side database and CouchDB (or compatible) as the server-side database. PouchDB provides built-in bidirectional sync with automatic conflict detection (revision trees).

**Why rejected:**

- Would require replacing PostgreSQL with CouchDB for the primary data store, or maintaining two databases (CouchDB for sync + PostgreSQL for relational queries). Both options are architecturally expensive.
- CouchDB's conflict resolution model (revision trees with manual conflict resolution) is more complex than needed. DentalOS's data model is primarily write-once-read-many for clinical records -- the simpler last-write-wins model is sufficient for most resources.
- PouchDB adds approximately 130 KB to the client bundle (gzipped). IndexedDB with a thin wrapper is lighter.
- The team would need to learn CouchDB administration and replication topology in addition to the existing PostgreSQL expertise.

**Trade-offs:** Excellent built-in sync protocol with proven reliability. But the architectural cost of adding CouchDB to the stack is not justified when the sync requirements are manageable with IndexedDB + custom sync logic.

### Alternative 3: CRDT-based Sync (Yjs, Automerge)

Use Conflict-free Replicated Data Types for automatic merge-without-conflict semantics. Each odontogram change is a CRDT operation that can be merged in any order without conflicts.

**Why rejected:**

- CRDTs are ideal for collaborative editing (like Google Docs) where multiple users edit the same document simultaneously. DentalOS's use case is predominantly single-user-per-patient-per-session -- true concurrent editing conflicts are rare.
- CRDT libraries (Yjs, Automerge) add significant bundle size and runtime overhead. Automerge's WASM build is ~300 KB.
- The mental model of CRDTs is complex for the development team to maintain. Debugging CRDT merge behavior is notoriously difficult.
- CRDT would be appropriate if DentalOS required real-time collaborative editing (e.g., two dentists editing the same odontogram simultaneously). The current requirement is offline tolerance, not real-time collaboration.

**Trade-offs:** Mathematically guaranteed conflict-free merges. But overkill for the actual conflict frequency in dental practice, and the complexity cost is high.

---

## Consequences

### Positive

- **Clinical continuity during outages.** Dentists can continue full clinical workflows (charting, notes, odontogram updates) during internet outages. Data is persisted locally and synced automatically when connectivity returns.
- **Competitive differentiator in LATAM.** Most competing dental software in the region is fully cloud-dependent. Offline support addresses a real pain point for clinics in areas with unreliable internet.
- **PWA-native implementation.** Service Workers, IndexedDB, and Background Sync are standard web platform APIs. No native app wrapper (Capacitor, Electron) is required, keeping the deployment model simple.
- **Graceful degradation.** The architecture degrades naturally from full-online to partial-offline to fully-offline, with clear UI indicators at each stage.

### Negative

- **Substantial frontend complexity.** The sync engine (queue management, conflict resolution, retry logic, status tracking) is a significant engineering effort. Estimated at 4-6 sprint weeks of development and testing.
- **Data integrity risks.** Offline data in IndexedDB is vulnerable to browser data clearing, incognito mode, and storage pressure eviction. Users must be warned that clearing browser data will lose unsynced changes.
- **Security trade-off.** Patient PHI stored in IndexedDB is not encrypted at rest on all platforms. This is a conscious trade-off: offline clinical functionality outweighs the risk, and the physical device security (device PIN, biometrics) provides a reasonable layer of protection.
- **Testing complexity.** Offline scenarios are difficult to test automatically. Requires Playwright or Cypress with network interception, Service Worker mocking, and IndexedDB state verification.
- **Conflict resolution edge cases.** While rare, concurrent edits to the same tooth surface by two clinicians will result in last-write-wins, potentially overwriting a legitimate clinical finding. The UI must surface conflict notifications so clinicians can review merged results.

### Neutral

- **MVP is unaffected.** This ADR describes the post-MVP architecture. The MVP uses simple optimistic UI with retry, which is already planned. The key constraint is that MVP code must not make assumptions that block the offline architecture (e.g., assuming server-assigned IDs are always available immediately -- use client-generated UUIDs instead).
- **Storage management.** IndexedDB usage must be monitored. DentalOS will implement a storage budget (warn at 80% capacity, refuse new offline writes at 95%) and provide a UI for users to view and manage cached data.
- **Browser support.** Service Workers and IndexedDB are supported in all modern browsers (Chrome, Firefox, Safari, Edge). Safari's Service Worker implementation has historically lagged but is now stable for PWA use cases.

---

## References

- [Service Worker API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [IndexedDB API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API)
- [Background Sync API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Background_Synchronization_API)
- [Workbox (Google)](https://developer.chrome.com/docs/workbox/) -- Service Worker toolbox
- [Storage Quota API](https://developer.mozilla.org/en-US/docs/Web/API/StorageManager/estimate) -- Monitoring browser storage usage
- [Navigator.connection API](https://developer.mozilla.org/en-US/docs/Web/API/NetworkInformation) -- Connection quality detection
- DentalOS `ADR-LOG.md` -- ADR-006 summary
- DentalOS `DOMAIN-GLOSSARY.md` -- PWA, Service Worker, IndexedDB definitions
