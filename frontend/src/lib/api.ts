/**
 * Typed API client for the DEI downloader backend.
 *
 * All requests go through the Vite dev proxy at /api/* in dev, and through
 * whatever host is configured in production. No credentials are sent.
 */

export type Availability = 'api' | 'manual' | 'subscription';

export interface Indicator {
  key: string;
  name: string;
  component: string;
  source: string;
  source_code: string;
  availability: Availability;
  unit: string;
  notes: string;
  manual_url: string;
  // Coverage metadata used for soft-greyout when the user picks a year range
  // outside the indicator's reporting window.
  earliest_year: number;
  latest_year: number;
  publication_lag_years: number;
  sparse: boolean;
}

/**
 * Whether an indicator has data in the selected year range. Mirrors the
 * backend's is_available_for_range() helper. Sparse indicators (Findex etc.)
 * are always treated as available because the user may legitimately pick a
 * year where the wave didn't run.
 */
export function isAvailableForRange(
  ind: Indicator,
  startYear: number,
  endYear: number,
): boolean {
  if (ind.sparse) return true;
  const effectiveLatest = Math.max(ind.earliest_year, ind.latest_year);
  return !(endYear < ind.earliest_year || startYear > effectiveLatest);
}

/**
 * Explain why an indicator isn't available for the current range. Used for
 * tooltips so the greyout isn't a mystery.
 */
export function unavailableReason(
  ind: Indicator,
  startYear: number,
  endYear: number,
): string | null {
  if (isAvailableForRange(ind, startYear, endYear)) return null;
  if (endYear < ind.earliest_year) {
    return `No data before ${ind.earliest_year}`;
  }
  if (startYear > ind.latest_year) {
    return `No data after ${ind.latest_year} (series last updated ${ind.latest_year})`;
  }
  return 'No data in selected range';
}

export interface PillarMeta {
  key: 'supply' | 'demand' | 'institutional' | 'innovation';
  label: string;
  indicators: Indicator[];
}

export interface Catalog {
  pillars: PillarMeta[];
  year_range: { min: number; max: number };
  source_summary: Record<string, { api: number; manual: number; subscription: number }>;
  availability_counts: Record<Availability, number>;
}

export interface Country {
  iso3: string;
  name: string;
  region: string;
}

export interface CountriesResponse {
  countries: Country[];
  by_region: Record<string, { iso3: string; name: string }[]>;
  total: number;
}

export interface SourceStatus {
  source: string;
  requested: number;
  fetched_rows: number;
  ok: boolean;
  message: string;
}

export interface PreviewResult {
  year_range: { start: number; end: number };
  total_rows: number;
  sources: SourceStatus[];
  rows_per_pillar: Record<string, number>;
}

export interface DownloadRequest {
  pillars: string[];
  start_year: number;
  end_year: number;
  countries?: string[];
  indicator_keys?: string[];
}

/**
 * Normalize the configured API base URL.
 *
 * Accepts three shapes and returns a URL you can concatenate with "/api/...":
 *   - empty string (dev with Vite proxy)      -> ""
 *   - bare hostname from Render fromService   -> "https://{host}"
 *   - full URL like "https://api.example.com" -> same, with trailing slash trimmed
 *
 * This lets render.yaml use `fromService property: hostport` (which emits a
 * bare hostname) without us having to hardcode https:// in the build config.
 */
function resolveApiBase(raw: string | undefined): string {
  if (!raw) return '';
  const trimmed = raw.trim().replace(/\/+$/, '');
  if (!trimmed) return '';
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  // localhost is always plain http
  if (trimmed.startsWith('localhost') || trimmed.startsWith('127.')) {
    return `http://${trimmed}`;
  }
  return `https://${trimmed}`;
}

const API_BASE = resolveApiBase(import.meta.env.VITE_API_BASE);

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ''}`);
  }
  return (await res.json()) as T;
}

// ============================================================================
// Catalog + countries
// ============================================================================

export async function getCatalog(): Promise<Catalog> {
  return request<Catalog>('/api/catalog');
}

export async function getCountries(): Promise<CountriesResponse> {
  return request<CountriesResponse>('/api/countries');
}

// ============================================================================
// Anthropic Economic Index — separate panel, its own endpoints
// ============================================================================

export interface AEIVariable {
  key: string;
  label: string;
}

export interface AEIPreview {
  available: boolean;
  message?: string;
  country_count: number;
  row_count?: number;
  variables: AEIVariable[];
  date_range: { start: string; end: string } | null;
  release?: string;
  license?: string;
  source_url?: string;
}

export async function getAEIPreview(): Promise<AEIPreview> {
  return request<AEIPreview>('/api/aei/preview');
}

export async function downloadAEI(): Promise<{ blob: Blob; filename: string }> {
  const resp = await fetch(`${API_BASE}/api/aei/download`);
  if (!resp.ok) {
    throw new Error(`AEI download failed: HTTP ${resp.status}`);
  }
  const blob = await resp.blob();
  const cd = resp.headers.get('Content-Disposition') || '';
  const match = cd.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : 'aei-country-panel.xlsx';
  return { blob, filename };
}

export async function preview(req: DownloadRequest): Promise<PreviewResult> {
  return request<PreviewResult>('/api/preview', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

/**
 * Trigger an xlsx download. Returns the blob and the suggested filename
 * parsed from Content-Disposition so the caller can drive the save flow.
 */
export async function downloadXlsx(
  req: DownloadRequest,
): Promise<{ blob: Blob; filename: string; totalRows: number }> {
  const res = await fetch(`${API_BASE}/api/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ''}`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get('content-disposition') ?? '';
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match?.[1] ?? `dei-indicators_${req.start_year}-${req.end_year}.xlsx`;
  const totalRows = Number(res.headers.get('x-total-rows') ?? '0');
  return { blob, filename, totalRows };
}

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
