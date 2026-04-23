import { useEffect, useMemo, useState } from 'react';
import {
  downloadXlsx,
  getCatalog,
  getCountries,
  isAvailableForRange,
  preview,
  saveBlob,
  type Catalog,
  type CountriesResponse,
  type Indicator,
  type PillarMeta,
  type PreviewResult,
} from './lib/api';
import { CountryPicker } from './components/CountryPicker';
import { SourcePicker } from './components/SourcePicker';
import { AEIPanel } from './components/AEIPanel';

// --------------------------------------------------------------------------
// Pillar card
// --------------------------------------------------------------------------

interface PillarCardProps {
  pillar: PillarMeta;
  index: number;
  selected: boolean;
  onToggle: () => void;
}

function PillarCard({ pillar, index, selected, onToggle }: PillarCardProps) {
  const counts = useMemo(() => {
    const c = { api: 0, manual: 0, subscription: 0 };
    for (const ind of pillar.indicators) c[ind.availability]++;
    return c;
  }, [pillar]);

  return (
    <button
      type="button"
      className={`pillar ${selected ? 'pillar--selected' : ''}`}
      onClick={onToggle}
      aria-pressed={selected}
    >
      <div className="pillar-check" />
      <div className="pillar-num">Pillar 0{index + 1}</div>
      <div className="pillar-name">{pillar.label}</div>
      <div className="pillar-count">
        <span><strong>{counts.api}</strong> api</span>
        {counts.manual > 0 && <span><strong>{counts.manual}</strong> manual</span>}
        {counts.subscription > 0 && <span><strong>{counts.subscription}</strong> sub.</span>}
      </div>
    </button>
  );
}

// --------------------------------------------------------------------------
// Year range slider
// --------------------------------------------------------------------------

interface YearRangeProps {
  min: number;
  max: number;
  start: number;
  end: number;
  onChange: (start: number, end: number) => void;
}

function YearRange({ min, max, start, end, onChange }: YearRangeProps) {
  const span = max - min;
  const startPct = span > 0 ? ((start - min) / span) * 100 : 0;
  const endPct = span > 0 ? ((end - min) / span) * 100 : 100;

  // Track which handle was most recently interacted with. When the two
  // handles are at the same value, the native browser z-order makes one
  // of them unreachable. By toggling a CSS class based on recent focus
  // we can lift the "wanted" handle above the other, letting the user
  // separate them again.
  const [lastGrabbed, setLastGrabbed] = useState<'start' | 'end'>('start');

  return (
    <div className="year-range">
      <div className="year-input-group">
        <div className="year-label">From</div>
        <div className="year-value">{start}</div>
      </div>

      <div
        className={`year-slider year-slider--last-${lastGrabbed}`}
      >
        <div className="year-slider-track" />
        <div
          className="year-slider-fill"
          style={{ left: `${startPct}%`, right: `${100 - endPct}%` }}
        />
        <input
          type="range"
          min={min}
          max={max}
          value={start}
          onChange={(e) => {
            const v = Math.min(Number(e.target.value), end);
            onChange(v, end);
          }}
          onPointerDown={() => setLastGrabbed('start')}
          onFocus={() => setLastGrabbed('start')}
          aria-label="Start year"
          data-side="start"
        />
        <input
          type="range"
          min={min}
          max={max}
          value={end}
          onChange={(e) => {
            const v = Math.max(Number(e.target.value), start);
            onChange(start, v);
          }}
          onPointerDown={() => setLastGrabbed('end')}
          onFocus={() => setLastGrabbed('end')}
          aria-label="End year"
          data-side="end"
        />
      </div>

      <div className="year-input-group" style={{ textAlign: 'right' }}>
        <div className="year-label">To</div>
        <div className="year-value">{end}</div>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
// Preview panel
// --------------------------------------------------------------------------

function PreviewPanel({ result }: { result: PreviewResult }) {
  return (
    <div className="preview-panel">
      <div className="preview-head">
        <div className="preview-head-title">Preview</div>
        <div className="preview-head-count">
          {result.total_rows.toLocaleString()} rows · {result.year_range.start}–{result.year_range.end}
        </div>
      </div>
      <div className="preview-body">
        {result.sources.map((s) => (
          <div key={s.source} className="preview-row">
            <div className={`preview-status preview-status--${s.ok ? 'ok' : 'fail'}`}>
              {s.ok ? '●' : '○'}
            </div>
            <div className="preview-source">{s.source}</div>
            <div className="preview-rows">
              <strong>{s.fetched_rows.toLocaleString()}</strong>
              <span style={{ color: 'var(--ink-mute)' }}> / {s.requested} ind.</span>
            </div>
            <div />
            {!s.ok && s.message && (
              <div className="preview-msg">{s.message}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
// Manual sources panel
// --------------------------------------------------------------------------

function ManualPanel({ pillars }: { pillars: PillarMeta[] }) {
  const manualInds = useMemo(() => {
    const seen = new Set<string>();
    const out: Indicator[] = [];
    for (const p of pillars) {
      for (const ind of p.indicators) {
        if (ind.availability === 'api') continue;
        if (seen.has(ind.key)) continue;
        seen.add(ind.key);
        out.push(ind);
      }
    }
    return out;
  }, [pillars]);

  if (manualInds.length === 0) return null;

  return (
    <div className="manual-panel">
      <div className="section-head">
        <div className="section-num">05</div>
        <h2 className="section-title">Sources requiring manual retrieval</h2>
        <div className="section-sub">{manualInds.length} indicators</div>
      </div>
      <p style={{ color: 'var(--ink-3)', fontSize: 14, marginBottom: 20, maxWidth: 680 }}>
        These indicators are not fetchable via a free API. Use the links below to either download
        them directly (ODIN, Transparency International, Freedom House) or access them through
        a subscription (Euromonitor via W&M's Swem library; EIU by institutional login).
      </p>
      <div className="manual-list">
        {manualInds.map((ind) => (
          <div key={ind.key} className="manual-item">
            <div className="manual-item-head">
              <div className="manual-item-name">{ind.name}</div>
              <div className={`source-badge source-badge--${ind.availability}`}>
                {ind.availability === 'manual' ? 'manual' : 'library'}
              </div>
            </div>
            <div className="manual-item-source">{ind.source}</div>
            {ind.notes && <div className="manual-item-notes">{ind.notes}</div>}
            {ind.manual_url && (
              <a
                href={ind.manual_url}
                target="_blank"
                rel="noopener noreferrer"
                className="manual-item-link"
              >
                Open source →
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
// App
// --------------------------------------------------------------------------

export default function App() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [countries, setCountries] = useState<CountriesResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedPillars, setSelectedPillars] = useState<Set<string>>(
    new Set(['supply', 'demand', 'institutional', 'innovation']),
  );
  const [selectedCountries, setSelectedCountries] = useState<Set<string>>(new Set());
  const [deselectedIndicators, setDeselectedIndicators] = useState<Set<string>>(new Set());

  const [startYear, setStartYear] = useState(2020);
  const [endYear, setEndYear] = useState(2025);

  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Load catalog and countries in parallel on mount
  useEffect(() => {
    Promise.all([getCatalog(), getCountries()])
      .then(([c, ctries]) => {
        setCatalog(c);
        setCountries(ctries);
        setStartYear(c.year_range.min);
        setEndYear(c.year_range.max);
        setSelectedCountries(new Set(ctries.countries.map((x) => x.iso3)));
      })
      .catch((e) => setLoadError(String(e.message ?? e)));
  }, []);

  const selectedPillarMetas = useMemo(() => {
    if (!catalog) return [];
    return catalog.pillars.filter((p) => selectedPillars.has(p.key));
  }, [catalog, selectedPillars]);

  // Indicators that are (a) in selected pillars, (b) not individually
  // deselected, AND (c) have data coverage in the current year range.
  // Greyed-out indicators are excluded from the fetch payload so the xlsx
  // doesn't contain empty rows — while their user-selection is preserved
  // in `deselectedIndicators` and will re-activate when the range widens.
  const activeIndicatorKeys = useMemo(() => {
    const keys: string[] = [];
    for (const p of selectedPillarMetas) {
      for (const ind of p.indicators) {
        if (ind.availability !== 'api') continue;
        if (deselectedIndicators.has(ind.key)) continue;
        if (!isAvailableForRange(ind, startYear, endYear)) continue;
        keys.push(ind.key);
      }
    }
    return keys;
  }, [selectedPillarMetas, deselectedIndicators, startYear, endYear]);

  // How many indicators could be active right now IF the user had everything
  // selected. Used to decide whether to send an `indicator_keys` filter or
  // leave it off (backend treats undefined as "all").
  const maxActiveIndicatorsInRange = useMemo(() => {
    let n = 0;
    for (const p of selectedPillarMetas) {
      for (const ind of p.indicators) {
        if (ind.availability !== 'api') continue;
        if (!isAvailableForRange(ind, startYear, endYear)) continue;
        n++;
      }
    }
    return n;
  }, [selectedPillarMetas, startYear, endYear]);

  function togglePillar(key: string) {
    invalidatePreview();
    setSelectedPillars((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function invalidatePreview() {
    setPreviewResult(null);
    setActionError(null);
  }

  // Build the filter-aware request object shared by preview + download.
  // If every country / every indicator is selected, omit the filter entirely
  // so the backend treats it as a no-op (smaller payload, simpler server state).
  function buildRequest() {
    if (!catalog || !countries) throw new Error('Not loaded');
    const totalCountries = countries.countries.length;
    const countryList =
      selectedCountries.size === totalCountries ? undefined : Array.from(selectedCountries);

    // "Full set" means "everything that CAN be active in the current range".
    // Using totalApiIndicatorsInPillars here would wrongly include unavailable
    // indicators; the backend would then reject the list or over-fetch.
    const isFullIndicatorSet = activeIndicatorKeys.length === maxActiveIndicatorsInRange;
    const indicatorList = isFullIndicatorSet ? undefined : activeIndicatorKeys;

    return {
      pillars: Array.from(selectedPillars),
      start_year: startYear,
      end_year: endYear,
      countries: countryList,
      indicator_keys: indicatorList,
    };
  }

  function canAct(): boolean {
    return (
      !!catalog &&
      !!countries &&
      selectedPillars.size > 0 &&
      selectedCountries.size > 0 &&
      activeIndicatorKeys.length > 0
    );
  }

  async function handlePreview() {
    if (!canAct()) return;
    setPreviewing(true);
    setActionError(null);
    try {
      const r = await preview(buildRequest());
      setPreviewResult(r);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setActionError(`Preview failed: ${msg}`);
    } finally {
      setPreviewing(false);
    }
  }

  async function handleDownload() {
    if (!canAct()) return;
    setDownloading(true);
    setActionError(null);
    try {
      const { blob, filename } = await downloadXlsx(buildRequest());
      saveBlob(blob, filename);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setActionError(`Download failed: ${msg}`);
    } finally {
      setDownloading(false);
    }
  }

  if (loadError) {
    return (
      <div className="page">
        <div className="error-banner">
          Could not load catalog from backend. Is the API running at /api?
          <br />
          <span style={{ opacity: 0.7 }}>{loadError}</span>
        </div>
      </div>
    );
  }

  if (!catalog || !countries) {
    return (
      <div className="page">
        <div className="loading">Loading catalog…</div>
      </div>
    );
  }

  const blocker = !canAct()
    ? selectedPillars.size === 0
      ? 'Select at least one pillar'
      : selectedCountries.size === 0
        ? 'Select at least one country'
        : activeIndicatorKeys.length === 0
          ? 'Enable at least one indicator'
          : ''
    : '';

  return (
    <div className="page">
      <header className="masthead">
        <div>
          <div className="masthead-eyebrow">Digital Evolution Index · Data bundler</div>
          <h1 className="masthead-title">
            Download the <em>underlying</em> indicators,<br />not just the scores.
          </h1>
        </div>
        <div className="masthead-meta">
          <div className="masthead-meta-row">
            <span className="masthead-meta-label">Vintage</span>
            <span className="masthead-meta-value">DEI 2025</span>
          </div>
          <div className="masthead-meta-row">
            <span className="masthead-meta-label">Catalog</span>
            <span className="masthead-meta-value">
              {catalog.availability_counts.api} API / {catalog.availability_counts.manual} manual / {catalog.availability_counts.subscription} sub.
            </span>
          </div>
          <div className="masthead-meta-row">
            <span className="masthead-meta-label">Economies</span>
            <span className="masthead-meta-value">{countries.total}</span>
          </div>
        </div>
      </header>

      <p className="lede">
        The Tufts Digital Evolution Index scores 125 economies on <strong>supply</strong>,{' '}
        <strong>demand</strong>, <strong>institutional environment</strong>, and{' '}
        <strong>innovation and change</strong>. Pick the pillars, countries, and sources you need;
        this tool pulls the raw indicators from free public APIs — World Bank, Findex, WGI, ITU,
        and the Anthropic Economic Index — and bundles them into a spreadsheet.
      </p>

      {actionError && <div className="error-banner">{actionError}</div>}

      {/* Step 1 — pillars */}
      <section className="section">
        <div className="section-head">
          <div className="section-num">01</div>
          <h2 className="section-title">Select pillars</h2>
          <div className="section-sub">{selectedPillars.size} / 4</div>
        </div>
        <div className="pillars">
          {catalog.pillars.map((p, i) => (
            <PillarCard
              key={p.key}
              pillar={p}
              index={i}
              selected={selectedPillars.has(p.key)}
              onToggle={() => togglePillar(p.key)}
            />
          ))}
        </div>
      </section>

      {/* Step 2 — countries */}
      <section className="section">
        <div className="section-head">
          <div className="section-num">02</div>
          <h2 className="section-title">Choose countries</h2>
          <div className="section-sub">
            {selectedCountries.size === countries.total
              ? 'all'
              : `${selectedCountries.size} / ${countries.total}`}
          </div>
        </div>
        <CountryPicker
          countries={countries.countries}
          byRegion={countries.by_region}
          selected={selectedCountries}
          onChange={(next) => {
            setSelectedCountries(next);
            invalidatePreview();
          }}
        />
      </section>

      {/* Step 3 — year range */}
      <section className="section">
        <div className="section-head">
          <div className="section-num">03</div>
          <h2 className="section-title">Choose year range</h2>
          <div className="section-sub">
            {endYear - startYear + 1} year{endYear - startYear === 0 ? '' : 's'}
          </div>
        </div>
        <YearRange
          min={catalog.year_range.min}
          max={catalog.year_range.max}
          start={startYear}
          end={endYear}
          onChange={(s, e) => {
            setStartYear(s);
            setEndYear(e);
            invalidatePreview();
          }}
        />
      </section>

      {/* Step 4 — sources */}
      <section className="section">
        <div className="section-head">
          <div className="section-num">04</div>
          <h2 className="section-title">Pick sources</h2>
          <div className="section-sub">auto · manual · library</div>
        </div>
        <SourcePicker
          pillars={catalog.pillars}
          selectedPillarKeys={selectedPillars}
          deselectedIndicatorKeys={deselectedIndicators}
          startYear={startYear}
          endYear={endYear}
          onChange={(next) => {
            setDeselectedIndicators(next);
            invalidatePreview();
          }}
        />
      </section>

      {/* Actions */}
      <div className="actions">
        <div className="actions-summary">
          <div className="actions-summary-main">
            <em>{activeIndicatorKeys.length}</em> indicators × <em>{selectedCountries.size}</em> countries
          </div>
          <div className="actions-summary-meta">
            {startYear}–{endYear} · {selectedPillars.size} pillar{selectedPillars.size === 1 ? '' : 's'} ·
            xlsx with one sheet per pillar
            {blocker && ` · ${blocker}`}
          </div>
        </div>
        <button
          type="button"
          className="btn btn--secondary"
          onClick={handlePreview}
          disabled={!canAct() || previewing || downloading}
        >
          {previewing ? 'Checking…' : 'Preview'}
        </button>
        <button
          type="button"
          className="btn btn--primary"
          onClick={handleDownload}
          disabled={!canAct() || downloading || previewing}
        >
          {downloading ? 'Building…' : 'Download xlsx'}
          <span className="btn-arrow">↓</span>
        </button>
      </div>

      {previewResult && <PreviewPanel result={previewResult} />}

      <ManualPanel pillars={selectedPillarMetas} />

      <AEIPanel startYear={startYear} endYear={endYear} />

      <footer className="footer">
        <div>
          Indicator catalog derived from Tufts Digital Planet · Digital Evolution Index 2025
        </div>
        <div>
          Not affiliated with Tufts · indicator data: public domain / CC-BY
        </div>
      </footer>
    </div>
  );
}
