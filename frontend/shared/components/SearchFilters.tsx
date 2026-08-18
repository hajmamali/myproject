import { LegalSearchFilters } from "../api/types";

interface SearchFiltersProps {
  filters: LegalSearchFilters;
  onChange: (filters: LegalSearchFilters) => void;
  limit: number;
  onLimitChange: (limit: number) => void;
  isOpen: boolean;
  onToggle: () => void;
}

/**
 * Input field with label
 */
function FilterInput({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: "text" | "number";
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-slate-300">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full border border-slate-600 rounded-lg text-sm bg-slate-900"
      />
    </div>
  );
}

/**
 * Checkbox input with label
 */
function FilterCheckbox({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-4 h-4 rounded border-slate-600 text-primary-600 focus:ring-primary-500"
      />
      <span className="text-sm text-slate-300">{label}</span>
    </label>
  );
}

/**
 * Select dropdown with label
 */
function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  options: { value: number; label: string }[];
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-slate-300">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full border border-slate-600 rounded-lg text-sm bg-slate-900"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

/**
 * Collapsible filters panel for search refinement
 */
export default function SearchFilters({
  filters,
  onChange,
  limit,
  onLimitChange,
  isOpen,
  onToggle,
}: SearchFiltersProps) {
  // Update a single filter field
  const updateFilter = <K extends keyof LegalSearchFilters>(
    key: K,
    value: LegalSearchFilters[K]
  ) => {
    onChange({ ...filters, [key]: value });
  };

  // Handle tags input (comma-separated)
  const handleTagsChange = (value: string) => {
    const tagsArray = value
      .split("،") // Persian comma
      .concat(value.split(",")) // English comma
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
    
    // Remove duplicates
    const uniqueTags = [...new Set(tagsArray)];
    updateFilter("tags", uniqueTags.length > 0 ? uniqueTags : null);
  };

  // Get current tags as comma-separated string
  const tagsString = filters.tags?.join("، ") || "";

  // Limit options
  const limitOptions = [
    { value: 5, label: "۵ نتیجه" },
    { value: 10, label: "۱۰ نتیجه" },
    { value: 20, label: "۲۰ نتیجه" },
    { value: 50, label: "۵۰ نتیجه" },
  ];

  return (
    <div className="border border-slate-700 rounded-xl bg-slate-900 overflow-hidden">
      {/* Toggle button */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-800 transition-colors"
        aria-expanded={isOpen}
      >
        <span className="flex items-center gap-2 text-sm font-medium text-slate-300">
          <svg
            className="w-5 h-5 text-slate-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
            />
          </svg>
          فیلترهای پیشرفته
        </span>
        <svg
          className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Filters panel */}
      {isOpen && (
        <div className="px-4 py-4 border-t border-slate-100 bg-slate-800/50">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Court level */}
            <FilterInput
              label="سطح دادگاه"
              value={filters.court_level || ""}
              onChange={(v) => updateFilter("court_level", v || null)}
              placeholder="مثال: دادگاه تجدیدنظر استان"
            />

            {/* Case type */}
            <FilterInput
              label="نوع پرونده"
              value={filters.case_type || ""}
              onChange={(v) => updateFilter("case_type", v || null)}
              placeholder="مثال: اعتراض ثالث اجرایی"
            />

            {/* Article number */}
            <FilterInput
              label="شماره ماده"
              value={filters.article_no || ""}
              onChange={(v) => updateFilter("article_no", v || null)}
              placeholder="مثال: 348"
            />

            {/* Law name */}
            <FilterInput
              label="نام قانون"
              value={filters.law_name || ""}
              onChange={(v) => updateFilter("law_name", v || null)}
              placeholder="مثال: قانون آیین دادرسی مدنی"
            />

            {/* Tags */}
            <FilterInput
              label="برچسب‌ها (با کاما جدا کنید)"
              value={tagsString}
              onChange={handleTagsChange}
              placeholder="مثال: رفع توقیف، اعتراض ثالث"
            />

            {/* Limit */}
            <FilterSelect
              label="تعداد نتایج"
              value={limit}
              onChange={onLimitChange}
              options={limitOptions}
            />
          </div>

          {/* Checkbox filters */}
          <div className="mt-4 pt-4 border-t border-slate-700 flex flex-wrap gap-6">
            <FilterCheckbox
              label="فقط آراء قطعی"
              checked={filters.is_final === true}
              onChange={(checked) => updateFilter("is_final", checked ? true : null)}
            />
          </div>

          {/* Clear filters button */}
          <div className="mt-4 pt-4 border-t border-slate-700">
            <button
              onClick={() => {
                onChange({});
                onLimitChange(10);
              }}
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              پاک کردن همه فیلترها
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

