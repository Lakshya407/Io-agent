import { Search } from "lucide-react";

export interface FilterOption {
  label: string;
  value: string;
  /** Either plain strings or `{ value, label }` pairs for richer lists. */
  options: string[] | { value: string; label: string }[];
  onChange: (value: string) => void;
}

interface FilterBarProps {
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  filters?: FilterOption[];
  dateValue?: string;
  onDateChange?: (value: string) => void;
}

function normalise(
  options: string[] | { value: string; label: string }[],
): { value: string; label: string }[] {
  return options.map((option) =>
    typeof option === "string" ? { value: option, label: option } : option,
  );
}

export default function FilterBar({
  searchValue,
  onSearchChange,
  searchPlaceholder = "Search…",
  filters = [],
  dateValue,
  onDateChange,
}: FilterBarProps) {
  return (
    <div className="filter-bar">
      {onSearchChange && (
        <div className="filter-search">
          <Search size={15} />
          <input
            type="text"
            value={searchValue ?? ""}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder={searchPlaceholder}
            aria-label={searchPlaceholder}
          />
        </div>
      )}
      {filters.map((filter) => (
        <select
          key={filter.label}
          className="filter-select"
          value={filter.value}
          onChange={(event) => filter.onChange(event.target.value)}
          aria-label={filter.label}
        >
          <option value="">{filter.label}: All</option>
          {normalise(filter.options).map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ))}
      {onDateChange && (
        <input
          type="date"
          className="filter-select"
          value={dateValue ?? ""}
          onChange={(event) => onDateChange(event.target.value)}
          aria-label="Date"
        />
      )}
    </div>
  );
}
