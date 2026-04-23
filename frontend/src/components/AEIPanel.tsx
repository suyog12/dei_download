import { useEffect, useMemo, useState } from 'react';
import {
  downloadAEI,
  getAEIPreview,
  saveBlob,
  type AEIPreview,
} from '../lib/api';

// The AEI 2025-09-15 release covers the data collection window of
// August 4-11, 2025. If the user's year range doesn't include 2025,
// the panel's data is from a different time than what they're looking at.
const AEI_DATA_YEAR = 2025;

interface AEIPanelProps {
  startYear: number;
  endYear: number;
}

/**
 * A standalone panel for Anthropic Economic Index country data.
 *
 * AEI is deliberately separated from DEI pillars because it's a different
 * kind of artifact: a point-in-time snapshot (not a year-indexed time series)
 * measuring AI adoption patterns that don't slot cleanly into DEI's
 * Supply/Demand/Institutional/Innovation framework.
 *
 * However, the panel does respect the user's year range. The AEI data window
 * (Aug 2025) only makes sense if 2025 is inside the selected range — otherwise
 * the panel greys itself out with a clear message, so users aren't confused
 * when they're looking at 2020-2021 data and still see 194 AEI countries.
 */
export function AEIPanel({ startYear, endYear }: AEIPanelProps) {
  const [preview, setPreview] = useState<AEIPreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inRange = useMemo(
    () => AEI_DATA_YEAR >= startYear && AEI_DATA_YEAR <= endYear,
    [startYear, endYear],
  );

  useEffect(() => {
    // Only hit the backend if the AEI data year is actually in the user's
    // selected range. Saves a HF round-trip and makes the out-of-range UX
    // consistent: same panel state whether the CSV is slow or just skipped.
    if (!inRange) {
      setPreview(null);
      return;
    }
    setLoadingPreview(true);
    getAEIPreview()
      .then((p) => setPreview(p))
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoadingPreview(false));
  }, [inRange]);

  async function handleDownload() {
    setDownloading(true);
    setError(null);
    try {
      const { blob, filename } = await downloadAEI();
      saveBlob(blob, filename);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(`AEI download failed: ${msg}`);
    } finally {
      setDownloading(false);
    }
  }

  const available = !!preview?.available;

  return (
    <section className={`aei-panel ${!inRange ? 'aei-panel--out-of-range' : ''}`}>
      <div className="aei-head">
        <div className="aei-head-eyebrow">Bonus panel · separate from DEI</div>
        <h2 className="aei-head-title">Anthropic Economic Index</h2>
        <p className="aei-head-sub">
          Country-level AI adoption from the Sept 2025 AEI release (CC-BY).
          This is a <em>snapshot</em> from August 2025, not a time series —
          it complements the DEI pillars rather than slotting into them.
        </p>
      </div>

      {!inRange && (
        <div className="aei-out-of-range">
          <strong>AEI data is from August 2025.</strong>{' '}
          Your selected range{' '}
          <span className="aei-range">
            {startYear === endYear ? startYear : `${startYear}–${endYear}`}
          </span>{' '}
          doesn't include 2025, so this panel is hidden to avoid mixing data
          from different time periods.
          <div className="aei-out-of-range-hint">
            Widen your range above to include 2025 if you want to see AEI data.
          </div>
        </div>
      )}

      {inRange && loadingPreview && (
        <div className="aei-loading">Checking AEI availability…</div>
      )}

      {inRange && preview && !available && (
        <div className="aei-unavailable">
          <strong>AEI data unreachable.</strong>{' '}
          {preview.message ||
            'The backend could not fetch the AEI CSV from Hugging Face.'}
        </div>
      )}

      {inRange && preview && available && (
        <>
          <div className="aei-stats">
            <div className="aei-stat">
              <div className="aei-stat-num">{preview.country_count}</div>
              <div className="aei-stat-label">countries</div>
            </div>
            <div className="aei-stat">
              <div className="aei-stat-num">{preview.variables.length}</div>
              <div className="aei-stat-label">metrics per country</div>
            </div>
            <div className="aei-stat aei-stat--wide">
              <div className="aei-stat-label">Data window</div>
              <div className="aei-stat-range">
                {preview.date_range?.start} → {preview.date_range?.end}
              </div>
            </div>
          </div>

          <div className="aei-variables">
            <div className="aei-variables-head">Variables included:</div>
            <ul className="aei-variables-list">
              {preview.variables.map((v) => (
                <li key={v.key}>
                  <span className="aei-var-code">{v.key}</span>
                  <span className="aei-var-label">{v.label}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="aei-actions">
            <div className="aei-actions-meta">
              {preview.release && <div className="aei-release">{preview.release}</div>}
              {preview.license && (
                <div className="aei-license">License: {preview.license}</div>
              )}
              {preview.source_url && (
                <a
                  href={preview.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="aei-source-link"
                >
                  View dataset on Hugging Face →
                </a>
              )}
            </div>
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleDownload}
              disabled={downloading}
            >
              {downloading ? 'Building…' : 'Download AEI xlsx'}
              <span className="btn-arrow">↓</span>
            </button>
          </div>
        </>
      )}

      {error && <div className="aei-error">{error}</div>}
    </section>
  );
}
