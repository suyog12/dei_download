import { useEffect, useMemo, useRef, useState } from 'react';
import type { Country } from '../lib/api';

interface CountryPickerProps {
  countries: Country[];
  byRegion: Record<string, { iso3: string; name: string }[]>;
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
}

const REGION_ORDER = [
  'Asia Pacific',
  'Europe & Central Asia',
  'Latin America & Caribbean',
  'Middle East & Africa',
  'North America',
];

/**
 * Multi-select country picker with type-ahead search.
 *
 * Default: all countries selected. The chip row shows selected countries;
 * typing filters the dropdown list. Region quick-selects live at the bottom
 * of the open panel for common bulk operations.
 */
export function CountryPicker({ countries, byRegion, selected, onChange }: CountryPickerProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) {
        setOpen(false);
        setQuery('');
      }
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return countries;
    return countries.filter(
      (c) => c.name.toLowerCase().includes(q) || c.iso3.toLowerCase().includes(q),
    );
  }, [query, countries]);

  const byRegionFiltered = useMemo(() => {
    const grouped: Record<string, Country[]> = {};
    for (const c of filtered) {
      (grouped[c.region] ??= []).push(c);
    }
    return grouped;
  }, [filtered]);

  function toggle(iso3: string) {
    const next = new Set(selected);
    if (next.has(iso3)) next.delete(iso3);
    else next.add(iso3);
    onChange(next);
  }

  function selectAll() {
    onChange(new Set(countries.map((c) => c.iso3)));
  }

  function selectNone() {
    onChange(new Set());
  }

  function toggleRegion(region: string) {
    const regionIsos = (byRegion[region] ?? []).map((c) => c.iso3);
    const allSelected = regionIsos.every((iso) => selected.has(iso));
    const next = new Set(selected);
    if (allSelected) {
      for (const iso of regionIsos) next.delete(iso);
    } else {
      for (const iso of regionIsos) next.add(iso);
    }
    onChange(next);
  }

  const selectedList = useMemo(
    () => countries.filter((c) => selected.has(c.iso3)),
    [countries, selected],
  );

  const allSelected = selected.size === countries.length;
  const noneSelected = selected.size === 0;

  return (
    <div className="country-picker" ref={containerRef}>
      <button
        type="button"
        className={`country-picker-trigger ${open ? 'is-open' : ''}`}
        onClick={() => {
          setOpen((o) => !o);
          setTimeout(() => inputRef.current?.focus(), 30);
        }}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="country-picker-count">
          {noneSelected ? (
            <em>No countries selected</em>
          ) : allSelected ? (
            <>All <strong>{countries.length}</strong> DEI economies</>
          ) : (
            <><strong>{selected.size}</strong> of {countries.length} selected</>
          )}
        </span>
        <span className="country-picker-caret">{open ? '▲' : '▼'}</span>
      </button>

      {/* Chip row — shows first N selected, "+X more" if overflow */}
      {!allSelected && !noneSelected && (
        <div className="country-chips">
          {selectedList.slice(0, 12).map((c) => (
            <span key={c.iso3} className="country-chip">
              {c.name}
              <button
                type="button"
                className="country-chip-remove"
                onClick={() => toggle(c.iso3)}
                aria-label={`Remove ${c.name}`}
              >
                ×
              </button>
            </span>
          ))}
          {selectedList.length > 12 && (
            <span className="country-chip country-chip--more">
              +{selectedList.length - 12} more
            </span>
          )}
        </div>
      )}

      {open && (
        <div className="country-picker-panel">
          <div className="country-picker-search">
            <input
              ref={inputRef}
              type="text"
              placeholder="Type a country name or ISO code…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="country-picker-input"
              aria-label="Search countries"
            />
            <div className="country-picker-bulk">
              <button
                type="button"
                className="country-picker-bulk-btn"
                onClick={selectAll}
              >
                Select all
              </button>
              <span className="country-picker-bulk-sep">·</span>
              <button
                type="button"
                className="country-picker-bulk-btn"
                onClick={selectNone}
              >
                Clear
              </button>
            </div>
          </div>

          <div className="country-picker-list">
            {REGION_ORDER.map((region) => {
              const regionCountries = byRegionFiltered[region];
              if (!regionCountries || regionCountries.length === 0) return null;
              const regionIsosInFull = byRegion[region]?.map((c) => c.iso3) ?? [];
              const regionAllSelected = regionIsosInFull.every((iso) => selected.has(iso));
              const regionSomeSelected = regionIsosInFull.some((iso) => selected.has(iso));

              return (
                <div key={region} className="country-region">
                  <div className="country-region-head">
                    <button
                      type="button"
                      className="country-region-toggle"
                      onClick={() => toggleRegion(region)}
                    >
                      <span
                        className={`country-region-check ${
                          regionAllSelected
                            ? 'is-full'
                            : regionSomeSelected
                              ? 'is-partial'
                              : ''
                        }`}
                      />
                      {region}
                    </button>
                    <span className="country-region-meta">
                      {regionIsosInFull.filter((iso) => selected.has(iso)).length} /{' '}
                      {regionIsosInFull.length}
                    </span>
                  </div>
                  <div className="country-region-list">
                    {regionCountries.map((c) => (
                      <label key={c.iso3} className="country-option">
                        <input
                          type="checkbox"
                          checked={selected.has(c.iso3)}
                          onChange={() => toggle(c.iso3)}
                        />
                        <span className="country-option-name">{c.name}</span>
                        <span className="country-option-iso">{c.iso3}</span>
                      </label>
                    ))}
                  </div>
                </div>
              );
            })}
            {filtered.length === 0 && (
              <div className="country-picker-empty">
                No countries match <strong>&ldquo;{query}&rdquo;</strong>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
