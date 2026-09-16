import {
  columnFacetingFeature,
  columnFilteringFeature,
  columnSizingFeature,
  columnVisibilityFeature,
  createExpandedRowModel,
  createFacetedRowModel,
  createFacetedUniqueValues,
  createFilteredRowModel,
  createSortedRowModel,
  filterFn_arrIncludesSome,
  filterFn_equalsString,
  filterFn_includesString,
  globalFilteringFeature,
  rowExpandingFeature,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_text,
  tableFeatures,
  type FilterFn,
  type Row,
} from "@tanstack/react-table";
import type { SurfaceRow } from "@/lib/surfaces";

/**
 * Global search. It matches the issue's required fields — surface, vendor,
 * family, region and retrieval status — via a single pre-built haystack so the
 * filter stays O(1) per row instead of scanning every column per keystroke.
 */
export const searchEverywhere: FilterFn<any, SurfaceRow> = (row: Row<any, SurfaceRow>, _columnId, filterValue) => {
  const needle = String(filterValue ?? "").trim().toLowerCase();
  if (!needle) return true;
  const terms = needle.split(/\s+/).filter(Boolean);
  const haystack = row.original.searchHaystack;
  return terms.every((term) => haystack.includes(term));
};

export const features = tableFeatures({
  rowSortingFeature,
  columnFilteringFeature,
  columnSizingFeature,
  globalFilteringFeature,
  columnFacetingFeature,
  columnVisibilityFeature,
  rowExpandingFeature,
  sortedRowModel: createSortedRowModel(),
  filteredRowModel: createFilteredRowModel(),
  facetedRowModel: createFacetedRowModel(),
  facetedUniqueValues: createFacetedUniqueValues(),
  expandedRowModel: createExpandedRowModel(),
  filterFns: {
    includesString: filterFn_includesString,
    equalsString: filterFn_equalsString,
    arrIncludesSome: filterFn_arrIncludesSome,
  },
  sortFns: {
    alphanumeric: sortFn_alphanumeric,
    text: sortFn_text,
  },
});

export type PlaneFeatures = typeof features;
