"use client";

import * as Popover from "@radix-ui/react-popover";
import { useId } from "react";

export interface FacetOption {
  value: string;
  label: string;
  count: number;
}

interface FacetFilterProps {
  name: string;
  label: string;
  options: FacetOption[];
  selected: string[];
  onChange: (values: string[]) => void;
}

/**
 * Faceted multi-select. Counts come from TanStack Table's faceted unique values,
 * so they reflect the other active filters rather than a static list.
 */
export function FacetFilter({ name, label, options, selected, onChange }: FacetFilterProps) {
  const id = useId();
  const toggle = (value: string) => {
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
  };
  const summary = selected.length === 0 ? "All" : selected.length === 1 ? labelFor(options, selected[0]) : `${selected.length} selected`;

  return (
    <div className="facet">
      <span className="facet-label" id={`${id}-label`}>
        {label}
      </span>
      <Popover.Root>
        <Popover.Trigger className="facet-trigger" aria-labelledby={`${id}-label`} data-testid={`facet-${name}`}>
          <span className="facet-value">{summary}</span>
          <span aria-hidden="true">▾</span>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content className="facet-content" align="start" sideOffset={4}>
            <div className="facet-header">
              <strong>{label}</strong>
              {selected.length > 0 ? (
                <button type="button" className="link-button" onClick={() => onChange([])}>
                  Clear
                </button>
              ) : null}
            </div>
            <ul className="facet-options">
              {options.map((option) => {
                const checked = selected.includes(option.value);
                return (
                  <li key={option.value}>
                    <label className="facet-option">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(option.value)}
                        data-testid={`facet-${name}-option-${option.value}`}
                      />
                      <span className="facet-option-label">{option.label}</span>
                      <span className="facet-count">{option.count}</span>
                    </label>
                  </li>
                );
              })}
            </ul>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </div>
  );
}

function labelFor(options: FacetOption[], value: string): string {
  return options.find((option) => option.value === value)?.label ?? value;
}
