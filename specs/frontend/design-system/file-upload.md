# File Upload — Design System Component Spec

## Overview

**Spec ID:** FE-DS-15

**Component:** `FileUpload`

**File:** `src/components/shared/file-upload.tsx`

**Description:** Drag-and-drop file upload zone with multi-file support, per-file progress bars, image thumbnail previews, and error states for invalid file types and size violations. Used for patient documents, clinic logo, consent templates (PDF), and clinical photos (radiographs, tooth photos).

**Design System Ref:** `FE-DS-01` (§11 file structure)

---

## Props Table

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `onFilesChange` | `(files: UploadedFile[]) => void` | — | Yes | Called with file list after add/remove |
| `accept` | `string[]` | `['*']` | No | Accepted MIME types or extensions. E.g., `['image/jpeg', '.pdf']` |
| `maxFiles` | `number` | `1` | No | Maximum number of files |
| `maxSizeMB` | `number` | `10` | No | Max file size per file in MB |
| `multiple` | `boolean` | `false` | No | Allow multiple files simultaneously |
| `uploadUrl` | `string` | — | No | If provided, component auto-uploads to this URL |
| `onUploadProgress` | `(fileId: string, progress: number) => void` | — | No | Upload progress callback |
| `disabled` | `boolean` | `false` | No | Disables the drop zone |
| `showPreview` | `boolean` | `true` | No | Show image thumbnails for image files |
| `label` | `string` | — | No | Label above the drop zone |
| `helperText` | `string` | — | No | Helper text below label |
| `error` | `string` | — | No | Error message displayed below zone |
| `existingFiles` | `ExistingFile[]` | `[]` | No | Pre-loaded files (from server) |
| `className` | `string` | — | No | Additional classes on wrapper |

---

## UploadedFile Type

```typescript
interface UploadedFile {
  id: string               // Local UUID assigned on selection
  file: File               // Native File object
  name: string
  size: number             // bytes
  type: string             // MIME type
  status: 'pending' | 'uploading' | 'success' | 'error'
  progress: number         // 0-100
  url?: string             // Set after successful upload
  errorMessage?: string    // Set when status is 'error'
  preview?: string         // Data URL for image preview
}

interface ExistingFile {
  id: string
  name: string
  url: string
  type: string
  size: number
  uploadedAt: string
}
```

---

## Visual Structure

```
[Label]
[Helper text]

+------------------------------------------+
|                                          |
|   [CloudUpload icon 40px]                |
|                                          |
|   Arrastra archivos aquí o              |
|   [haz clic para seleccionar]           |
|                                          |
|   JPG, PNG, PDF · Máx. 10 MB            |
|                                          |
+------------------------------------------+

[File preview list]
  [thumb/icon] filename.pdf     2.3 MB  [X]
               [===       ] 45%
  [thumb/icon] photo.jpg        1.1 MB  [X]
               [==========] ✓ Subido

[Error message]
```

---

## Drop Zone States

### Default (empty, no files)

```
border-2 border-dashed border-gray-300 rounded-xl
bg-white
p-8 text-center cursor-pointer
hover:border-teal-400 hover:bg-teal-50
transition-colors duration-200
```

### Drag Active (file being dragged over)

```
border-2 border-dashed border-teal-500 rounded-xl
bg-teal-50 scale-[1.01]
transition-all duration-150
```

**Icon changes:** `CloudUpload` icon animates with slight bounce.

**Text:** "Suelta el archivo aquí"

### Disabled

```
border-2 border-dashed border-gray-200 rounded-xl
bg-gray-50 cursor-not-allowed opacity-60
```

### Error State

```
border-2 border-dashed border-red-400 rounded-xl
bg-red-50
```

Error message: `text-xs text-red-600 mt-2` below the zone.

### Has Files (zone shrinks)

Once files are added, the drop zone reduces to a compact secondary state:

```
border border-dashed border-gray-200 rounded-lg
bg-gray-50 py-3 px-4 text-sm text-gray-500 text-center
cursor-pointer hover:bg-gray-100
```

Text: "+ Agregar más archivos" (or hidden if `maxFiles` reached).

---

## Drop Zone Content (default state)

```
[CloudUpload icon]         ← w-10 h-10 text-gray-400
"Arrastra archivos aquí"   ← text-sm font-medium text-gray-700
"o"                        ← text-sm text-gray-500
"haz clic para seleccionar"← text-sm text-teal-600 underline font-medium (link-like)

"JPG, PNG, PDF · Máx. 10 MB" ← text-xs text-gray-400 mt-2
```

Accepted types and size shown dynamically from props:
- `accept=['image/jpeg', 'image/png']` → "JPG, PNG"
- `maxSizeMB=5` → "Máx. 5 MB"

---

## File Preview List

After files are added, each file is shown as a row:

### Image Files (with thumbnail)

```
+------------------------------------------+
| [48x48 thumb]  photo.jpg          [X]    |
|                1.2 MB                    |
|                [==========] ✓ Subido    |
+------------------------------------------+
```

**Thumbnail:** 48x48px, `rounded-md object-cover`, generated from `URL.createObjectURL(file)`.

### Non-image Files (document icon)

```
+------------------------------------------+
| [FileText]     documento.pdf      [X]    |
|                2.3 MB                    |
|                [======    ] 60%         |
+------------------------------------------+
```

**Icon by type:**
- `.pdf`: `FileText` icon, red-100 bg
- `.docx`, `.doc`: `FileText` icon, blue-100 bg
- `.xlsx`, `.csv`: `Table` icon, green-100 bg
- Other: `File` icon, gray-100 bg

### Progress Bar

`h-1.5 rounded-full bg-gray-200` track.
Inner: `bg-teal-500 rounded-full` fill, width = `${progress}%`, transitions smoothly.

**States:**
- Uploading: `bg-teal-500 animate-[width]` (CSS transition on width)
- Success: `bg-green-500` full width + `CheckCircle2` icon replaces progress bar
- Error: `bg-red-500 h-1.5` + error message below

---

## Remove Button

`X` icon button at right of each file row:

```
Button ghost size="sm" w-8 h-8 p-0
aria-label="Eliminar [filename]"
```

For `status='success'` (already uploaded): clicking removes the file from local list AND calls DELETE API if `uploadUrl` is configured.

For `status='pending'` or `'uploading'`: removes from local list only (cancels upload if in progress).

---

## File Validation

Validation runs on file selection (not on drop zone click — only when files are actually dropped or selected):

### Type Validation

```typescript
function isValidType(file: File, accept: string[]): boolean {
  return accept.some(type => {
    if (type.startsWith('.')) return file.name.toLowerCase().endsWith(type.toLowerCase())
    if (type.includes('*')) return file.type.startsWith(type.split('*')[0])
    return file.type === type
  })
}
```

**Error message:** "Tipo de archivo no permitido. Acepta: [accepted types list]"

### Size Validation

```typescript
function isValidSize(file: File, maxSizeMB: number): boolean {
  return file.size <= maxSizeMB * 1024 * 1024
}
```

**Error message:** "El archivo '[name]' supera el límite de [maxSizeMB] MB (tamaño actual: [actual]MB)"

### Count Validation

If adding files would exceed `maxFiles`: oldest pending file replaced or error shown.

**Error message:** "Máximo [maxFiles] archivo(s) permitido(s)"

---

## Auto-upload Mode

When `uploadUrl` is provided, files upload automatically on selection:

```typescript
async function uploadFile(file: UploadedFile) {
  const formData = new FormData()
  formData.append('file', file.file)

  const xhr = new XMLHttpRequest()
  xhr.upload.addEventListener('progress', (e) => {
    const progress = Math.round((e.loaded / e.total) * 100)
    onUploadProgress?.(file.id, progress)
  })
  xhr.open('POST', uploadUrl)
  xhr.setRequestHeader('Authorization', `Bearer ${token}`)
  xhr.send(formData)
}
```

**XHR used over fetch** to support upload progress events.

---

## Usage Examples

```tsx
// Single image upload (logo)
<FileUpload
  label="Logo de la clínica"
  accept={['image/jpeg', 'image/png', 'image/svg+xml', 'image/webp']}
  maxFiles={1}
  maxSizeMB={2}
  showPreview
  uploadUrl="/api/v1/tenants/logo"
  onFilesChange={(files) => setValue('logo', files[0]?.url)}
/>

// Multiple patient documents
<FileUpload
  label="Documentos del paciente"
  helperText="Puedes subir múltiples archivos a la vez"
  accept={['application/pdf', 'image/jpeg', 'image/png']}
  maxFiles={10}
  maxSizeMB={20}
  multiple
  uploadUrl={`/api/v1/patients/${patientId}/documents`}
  existingFiles={patient.documents}
  onFilesChange={handleDocumentChange}
/>

// Radiograph upload
<FileUpload
  label="Radiografías"
  accept={['image/jpeg', 'image/png', 'image/dicom']}
  maxFiles={5}
  maxSizeMB={50}
  multiple
  showPreview
  onFilesChange={setRadiographFiles}
/>
```

---

## Accessibility

- **Drop zone:** `role="button"`, `tabIndex={0}`, `aria-label="Área de subida de archivos. Presiona Enter para abrir el selector de archivos."`, `aria-describedby` pointing to accepted types text.
- **Drag active:** `aria-live="polite"` region announces "Archivo detectado. Suelta para agregar."
- **File list:** `role="list"`, each file row is `role="listitem"`.
- **Remove button:** `aria-label="Eliminar [filename]"`.
- **Progress:** `role="progressbar"` with `aria-valuenow`, `aria-valuemin=0`, `aria-valuemax=100`, `aria-label="Subiendo [filename]"`.
- **Upload complete:** `aria-live="polite"` announces "[filename] subido exitosamente."
- **Error:** `role="alert"` on validation error messages.
- **Keyboard:** Enter/Space on drop zone opens file picker. Tab navigates file rows. Delete/Backspace on focused row removes file.

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Drop zone full width. File preview list single column. Touch drag-and-drop supported. |
| Tablet (640-1024px) | Drop zone full width. Image previews may show 2-column grid. |
| Desktop (> 1024px) | Drop zone width constrained by parent card/form column. |

---

## Implementation Notes

**File Location:** `src/components/shared/file-upload.tsx`

**Dependencies:**
- No external library needed for basic drop zone (use native `DragEvent` + `<input type="file">`)
- Optional: `react-dropzone` for more robust cross-browser support

**Hook:** `useFileUpload()` custom hook encapsulates upload state, validation, and XHR management.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec |
