import { LegalSearchHit } from "../api/types";
import { InboxIcon, MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import ResultCard from "./ResultCard";

interface ResultsListProps {
  results: LegalSearchHit[];
  isLoading: boolean;
  hasSearched: boolean;
}

/**
 * Loading spinner component
 */
function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      <p className="mt-4 text-slate-400">در حال جستجو...</p>
    </div>
  );
}

/**
 * Empty state when no results found
 */
function EmptyState({ hasSearched }: { hasSearched: boolean }) {
  if (!hasSearched) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-20 h-20 rounded-full bg-slate-800/80 flex items-center justify-center mb-4 border border-slate-700">
          <MagnifyingGlassIcon className="w-8 h-8 text-slate-500" />
        </div>
        <h3 className="text-lg font-medium text-slate-300 mb-2">
          جستجوی آراء حقوقی
        </h3>
        <p className="text-slate-500 max-w-md">
          سوال حقوقی خود را در کادر بالا وارد کنید و روی دکمه «جستجو» کلیک کنید.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-20 h-20 rounded-full bg-accent-50 flex items-center justify-center mb-4 border border-accent-200">
        <InboxIcon className="w-8 h-8 text-accent-600" />
      </div>
      <h3 className="text-lg font-medium text-slate-300 mb-2">
        نتیجه‌ای یافت نشد
      </h3>
      <p className="text-slate-500 max-w-md">
        هیچ رأیی با معیارهای جستجوی شما یافت نشد.
        <br />
        لطفاً عبارت جستجو یا فیلترها را تغییر دهید.
      </p>
    </div>
  );
}

/**
 * Results summary header
 */
function ResultsSummary({ count }: { count: number }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-lg font-semibold text-slate-200">
        نتایج جستجو
      </h2>
      <span className="text-sm text-slate-500">
        {count} نتیجه یافت شد
      </span>
    </div>
  );
}

/**
 * List component for displaying search results
 */
export default function ResultsList({ results, isLoading, hasSearched }: ResultsListProps) {
  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (results.length === 0) {
    return <EmptyState hasSearched={hasSearched} />;
  }

  return (
    <div>
      <ResultsSummary count={results.length} />
      
      <div className="space-y-4">
        {results.map((hit, index) => (
          <ResultCard 
            key={`${hit.verdict_id}-${index}`} 
            hit={hit} 
            index={index} 
          />
        ))}
      </div>
    </div>
  );
}
