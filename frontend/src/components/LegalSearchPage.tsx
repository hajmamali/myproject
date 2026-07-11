import { useState, useCallback, FormEvent } from "react";
import { ScaleIcon } from "@heroicons/react/24/outline";
import { LegalSearchFilters, LegalSearchHit } from "../api/types";
import { searchVerdicts, SearchAPIError } from "../api/client";
import SearchFilters from "./SearchFilters";
import ResultsList from "./ResultsList";
import UploadModal from "./UploadModal";
import ExportButton from "./ExportButton";
import StatsPanel from "./StatsPanel";

/**
 * Main page component for legal verdict search
 */
export default function LegalSearchPage() {
  // Search state
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<LegalSearchFilters>({});
  const [limit, setLimit] = useState(10);

  // Results state
  const [results, setResults] = useState<LegalSearchHit[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  /**
   * Handle search submission
   */
  const handleSearch = useCallback(async (e?: FormEvent) => {
    e?.preventDefault();

    // Validate query
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError("لطفاً عبارت جستجو را وارد کنید.");
      return;
    }

    // Reset state
    setIsLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const response = await searchVerdicts({
        query: trimmedQuery,
        filters: Object.keys(filters).length > 0 ? filters : null,
        limit,
        enrich_with_graph: true,
      });

      setResults(response.results);

    } catch (err) {
      console.error("Search error:", err);

      if (err instanceof SearchAPIError) {
        setError(err.message);
      } else {
        setError("خطای غیرمنتظره در انجام جستجو. لطفاً دوباره تلاش کنید.");
      }

      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, [query, filters, limit]);

  /**
   * Handle keyboard shortcut (Ctrl/Cmd + Enter)
   */
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      handleSearch();
    }
  }, [handleSearch]);

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-gradient-to-l from-primary-900 via-primary-800 to-primary-700 text-white">
        <div className="max-w-5xl mx-auto px-4 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-slate-900/10 border border-white/15 flex items-center justify-center">
                <ScaleIcon className="w-7 h-7 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">ماحون</h1>
                <p className="text-primary-100 text-sm">سامانه هوشمند جستجوی آراء حقوقی</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setUploadModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2 bg-slate-900/10 hover:bg-slate-900/20 border border-white/15 rounded-lg transition-colors text-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                آپلود سند
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-4 -mt-4 page-enter">
        {/* Search box */}
        <div className="bg-slate-900 rounded-2xl shadow-xl border border-slate-700 overflow-hidden">
          <form onSubmit={handleSearch}>
            {/* Query input */}
            <div className="p-4">
              <label htmlFor="search-query" className="sr-only">
                عبارت جستجو
              </label>
              <div className="relative">
                <textarea
                  id="search-query"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="سوال حقوقی خود را وارد کنید... (مثال: اعتراض ثالث اجرایی نسبت به توقیف عملیات اجرای احکام)"
                  rows={3}
                  className="w-full border border-slate-700 rounded-xl resize-none text-base leading-relaxed bg-slate-800 focus:bg-slate-900 transition-colors"
                  dir="rtl"
                />
                <div className="absolute bottom-3 left-3 text-xs text-slate-400">
                  Ctrl + Enter برای جستجو
                </div>
              </div>
            </div>

            {/* Filters */}
            <div className="px-4 pb-4">
              <SearchFilters
                filters={filters}
                onChange={setFilters}
                limit={limit}
                onLimitChange={setLimit}
                isOpen={filtersOpen}
                onToggle={() => setFiltersOpen(!filtersOpen)}
              />
            </div>

            {/* Search button */}
            <div className="px-4 pb-4 flex items-center justify-between">
              <button
                type="submit"
                disabled={isLoading}
                className="flex items-center gap-2 px-6 py-3 bg-primary-700 hover:bg-primary-800 disabled:bg-primary-400 text-white font-medium rounded-xl transition-colors shadow-sm"
              >
                {isLoading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    در حال جستجو...
                  </>
                ) : (
                  <>
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                      />
                    </svg>
                    جستجو
                  </>
                )}
              </button>

              {/* Active filters indicator */}
              {Object.values(filters).some((v) => v !== null && v !== undefined) && (
                <span className="text-sm text-primary-700">
                  فیلترهای فعال: {Object.values(filters).filter((v) => v !== null && v !== undefined).length}
                </span>
              )}
            </div>
          </form>
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
            <div className="flex items-start gap-3">
              <svg
                className="w-5 h-5 flex-shrink-0 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div>
                <p className="font-medium">خطا در جستجو</p>
                <p className="mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Results section */}
        <section className="mt-6 pb-12">
          {hasSearched && results.length > 0 && (
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-4">
                <h2 className="text-lg font-bold text-slate-200">
                  نتایج جستجو ({results.length.toLocaleString('fa-IR')})
                </h2>
                <ExportButton results={results} query={query} />
              </div>
              <StatsPanel />
            </div>
          )}
          <ResultsList
            results={results}
            isLoading={isLoading}
            hasSearched={hasSearched}
          />
        </section>
      </main>

      {/* Upload Modal */}
      <UploadModal isOpen={uploadModalOpen} onClose={() => setUploadModalOpen(false)} />

      {/* Footer */}
      <footer className="border-t border-slate-700 bg-slate-900 mt-auto">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <div className="flex flex-wrap items-center justify-between gap-4 text-sm text-slate-500">
            <p>
              سامانه هوشمند جستجوی آراء حقوقی ماحون
            </p>
            <p>
              نسخه ۱.۰.۰
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
