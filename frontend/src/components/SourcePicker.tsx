import { useMemo, useState } from 'react';
import {
  isAvailableForRange,
  unavailableReason,
  type Availability,
  type Indicator,
  type PillarMeta,
} from '../lib/api';

interface SourcePickerProps {
  pillars: PillarMeta[];
  selectedPillarKeys: Set<string>;
  deselectedIndicatorKeys: Set<string>;
  onChange: (deselected: Set<string>) => void;
  // Needed to compute soft-greyout for indicators without coverage in the
  // current year range. We only visually disable them; we don't mutate the
  // user's deselection set (that way dragging the slider back makes them
  // light up again).
  startYear: number;
  endYear: number;
}

interface SourceGroup {
  source: string;
  availability: Availability;
  indicators: Indicator[];
}

const RANK: Record<Availability, number> = { api: 3, manual: 2, subscription: 1 };

/**
 * Group indicators from the selected pillars by source, then by availability.
 * API sources come first (they're what we actually fetch). Manual and
 * subscription sources are shown at the bottom and can't be "deselected" in
 * a meaningful way because we don't fetch them — but we show them for
 * visibility.
 */
function collectGroups(pillars: PillarMeta[]): SourceGroup[] {
  const map = new Map<string, SourceGroup>();
  for (const p of pillars) {
    for (const ind of p.indicators) {
      const existing = map.get(ind.source);
      if (!existing) {
        map.set(ind.source, {
          source: ind.source,
          availability: ind.availability,
          indicators: [ind],
        });
      } else {
        existing.indicators.push(ind);
        if (RANK[ind.availability] > RANK[existing.availability]) {
          existing.availability = ind.availability;
        }
      }
    }
  }
  return Array.from(map.values()).sort((a, b) => {
    const r = RANK[b.availability] - RANK[a.availability];
    return r !== 0 ? r : a.source.localeCompare(b.source);
  });
}

export function SourcePicker({
  pillars,
  selectedPillarKeys,
  deselectedIndicatorKeys,
  onChange,
  startYear,
  endYear,
}: SourcePickerProps) {
  const [expanded, setExpanded] = useState(false);

  const selectedPillars = useMemo(
    () => pillars.filter((p) => selectedPillarKeys.has(p.key)),
    [pillars, selectedPillarKeys],
  );

  const groups = useMemo(() => collectGroups(selectedPillars), [selectedPillars]);

  // Precompute which indicators are *unavailable* in the current year range.
  // We do this once per render of the picker rather than re-deriving on every
  // click. Sparse indicators never land in this set (see isAvailableForRange).
  const unavailableKeys = useMemo(() => {
    const s = new Set<string>();
    for (const g of groups) {
      for (const ind of g.indicators) {
        if (!isAvailableForRange(ind, startYear, endYear)) s.add(ind.key);
      }
    }
    return s;
  }, [groups, startYear, endYear]);

  if (groups.length === 0) {
    return (
      <div className="source-empty">
        Select at least one pillar above to see its data sources.
      </div>
    );
  }

  function isEffectivelyActive(ind: Indicator): boolean {
    // Active = user has it selected AND the year range supports it.
    // This is the single source of truth for what ships in the fetch payload.
    if (deselectedIndicatorKeys.has(ind.key)) return false;
    if (unavailableKeys.has(ind.key)) return false;
    return true;
  }

  function sourceState(group: SourceGroup): 'full' | 'partial' | 'empty' {
    // Only count AVAILABLE indicators toward the source's check state;
    // otherwise a source with one greyed-out indicator would always look
    // "partial" even when every selectable indicator is checked.
    const selectable = group.indicators.filter((i) => !unavailableKeys.has(i.key));
    if (selectable.length === 0) return 'empty';
    const deselectedInGroup = selectable.filter((i) =>
      deselectedIndicatorKeys.has(i.key),
    ).length;
    if (deselectedInGroup === 0) return 'full';
    if (deselectedInGroup === selectable.length) return 'empty';
    return 'partial';
  }

  function toggleSource(group: SourceGroup) {
    // Only toggle AVAILABLE indicators — the rest are greyed out regardless.
    const state = sourceState(group);
    const next = new Set(deselectedIndicatorKeys);
    const selectable = group.indicators.filter((i) => !unavailableKeys.has(i.key));
    if (state === 'full') {
      for (const ind of selectable) next.add(ind.key);
    } else {
      for (const ind of selectable) next.delete(ind.key);
    }
    onChange(next);
  }

  function toggleIndicator(key: string) {
    // Can't toggle an unavailable indicator — the checkbox is disabled anyway,
    // but defend against programmatic calls too.
    if (unavailableKeys.has(key)) return;
    const next = new Set(deselectedIndicatorKeys);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    onChange(next);
  }

  function selectAll() {
    onChange(new Set());
  }

  function selectNone() {
    // "All off" should only deselect currently-available indicators so that
    // when the user widens the range, nothing unexpected lights up.
    const next = new Set<string>();
    for (const g of groups) {
      for (const ind of g.indicators) {
        if (!unavailableKeys.has(ind.key)) next.add(ind.key);
      }
    }
    onChange(next);
  }

  const totalIndicators = groups.reduce((n, g) => n + g.indicators.length, 0);
  const activeIndicators = groups.reduce(
    (n, g) => n + g.indicators.filter(isEffectivelyActive).length,
    0,
  );
  const greyedOutCount = unavailableKeys.size;

  return (
    <div className="source-picker">
      <div className="source-picker-head">
        <div className="source-picker-summary">
          <strong>{activeIndicators}</strong> of {totalIndicators} indicators active
          {greyedOutCount > 0 && (
            <span className="source-picker-greyed">
              {' · '}
              <span>{greyedOutCount} unavailable for {startYear}–{endYear}</span>
            </span>
          )}
        </div>
        <div className="source-picker-bulk">
          <button
            type="button"
            className="country-picker-bulk-btn"
            onClick={selectAll}
          >
            All on
          </button>
          <span className="country-picker-bulk-sep">·</span>
          <button
            type="button"
            className="country-picker-bulk-btn"
            onClick={selectNone}
          >
            All off
          </button>
        </div>
      </div>

      {/* Source-level toggles */}
      <div className="sources">
        {groups.map((g) => {
          const state = sourceState(g);
          const isDeselectable = g.availability === 'api';
          const selectableCount = g.indicators.filter((i) => !unavailableKeys.has(i.key)).length;
          const activeCount = g.indicators.filter(isEffectivelyActive).length;
          const allGreyedOut = selectableCount === 0 && isDeselectable;
          return (
            <button
              type="button"
              key={g.source}
              className={`source source--${g.availability} source-toggle source-toggle--${state} ${allGreyedOut ? 'source-toggle--unavailable' : ''}`}
              onClick={isDeselectable && !allGreyedOut ? () => toggleSource(g) : undefined}
              disabled={!isDeselectable || allGreyedOut}
              title={
                !isDeselectable
                  ? 'This source is manual/library — not fetched automatically'
                  : allGreyedOut
                    ? `No indicators from this source have data in ${startYear}–${endYear}`
                    : ''
              }
            >
              <div className={`source-toggle-check source-toggle-check--${state}`} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="source-name">{g.source}</div>
                <div className="source-meta">
                  {isDeselectable ? (
                    <>
                      {activeCount} / {g.indicators.length} indicator{g.indicators.length === 1 ? '' : 's'}
                      {selectableCount < g.indicators.length && (
                        <span className="source-meta-greyed">
                          {' · '}
                          {g.indicators.length - selectableCount} unavailable
                        </span>
                      )}
                    </>
                  ) : (
                    `${g.indicators.length} indicator${g.indicators.length === 1 ? '' : 's'}`
                  )}
                </div>
              </div>
              <div className={`source-badge source-badge--${g.availability}`}>
                {g.availability === 'api' ? 'auto' : g.availability === 'manual' ? 'manual' : 'library'}
              </div>
            </button>
          );
        })}
      </div>

      {/* Advanced expander — per-indicator toggles */}
      <button
        type="button"
        className="source-advanced-toggle"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
      >
        <span className="source-advanced-chevron">{expanded ? '▾' : '▸'}</span>
        Advanced — toggle individual indicators
      </button>

      {expanded && (
        <div className="source-advanced-panel">
          {groups
            .filter((g) => g.availability === 'api')
            .map((g) => {
              const selectableCount = g.indicators.filter((i) => !unavailableKeys.has(i.key)).length;
              const activeCount = g.indicators.filter(isEffectivelyActive).length;
              return (
                <div key={g.source} className="source-advanced-group">
                  <div className="source-advanced-group-head">
                    <div className="source-advanced-group-name">{g.source}</div>
                    <div className="source-advanced-group-meta">
                      {activeCount} / {selectableCount === g.indicators.length
                        ? g.indicators.length
                        : `${selectableCount} available`}
                    </div>
                  </div>
                  <div className="source-advanced-group-list">
                    {g.indicators.map((ind) => {
                      const unavailable = unavailableKeys.has(ind.key);
                      const reason = unavailable
                        ? unavailableReason(ind, startYear, endYear)
                        : null;
                      const active = !deselectedIndicatorKeys.has(ind.key) && !unavailable;
                      return (
                        <label
                          key={ind.key}
                          className={`indicator-option ${unavailable ? 'indicator-option--unavailable' : ''}`}
                          title={reason ?? ''}
                        >
                          <input
                            type="checkbox"
                            checked={active}
                            disabled={unavailable}
                            onChange={() => toggleIndicator(ind.key)}
                          />
                          <span className="indicator-option-body">
                            <span className="indicator-option-name">{ind.name}</span>
                            <span className="indicator-option-meta">
                              <span className="indicator-option-component">{ind.component}</span>
                              <span className="indicator-option-code">{ind.source_code}</span>
                              {reason && (
                                <span className="indicator-option-unavailable">
                                  {reason}
                                </span>
                              )}
                            </span>
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
