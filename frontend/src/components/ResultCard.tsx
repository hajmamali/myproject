import { LegalSearchHit } from "../api/types";
import { DocumentTextIcon } from "@heroicons/react/24/outline";

interface ResultCardProps {
  hit: LegalSearchHit;
  index: number;
}

/**
 * Section name translations
 */
const sectionLabels: Record<string, string> = {
  overview: "خلاصه پرونده",
  first_instance_summary: "رأی بدوی",
  appeal_reasoning: "استدلال تجدیدنظر",
  legal_references: "مستندات قانونی",
  parties: "اطراف دعوا",
  claims: "خواسته‌ها",
  unknown: "بخش نامشخص",
};

/**
 * Card component for displaying a single verdict search result
 */
export default function ResultCard({ hit, index }: ResultCardProps) {
  // Format score as percentage
  const scorePercent = Math.round(hit.score * 100);
  
  // Get translated section label
  const sectionLabel = sectionLabels[hit.section] || hit.section;

  return (
    <article 
      className="bg-slate-900 rounded-xl shadow-sm border border-slate-700 overflow-hidden card-hover"
      role="article"
      aria-labelledby={`result-title-${index}`}
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 bg-slate-800/50">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Left: Case info */}
          <div className="flex flex-wrap items-center gap-2">
            {hit.case_type && (
              <h3 
                id={`result-title-${index}`}
                className="font-bold text-slate-200 text-sm"
              >
                {hit.case_type}
              </h3>
            )}
            
            {hit.court_level && (
              <span className="text-xs text-slate-500 bg-slate-800/80 px-2 py-1 rounded">
                {hit.court_level}
              </span>
            )}
            
            {hit.procedure_stage && (
              <span className="text-xs text-slate-500">
                مرحله: {hit.procedure_stage}
              </span>
            )}
          </div>

          {/* Right: Score and status */}
          <div className="flex items-center gap-3">
            {/* Final status badge */}
            {hit.is_final !== null && hit.is_final !== undefined && (
              <span
                className={`pill ${
                  hit.is_final ? "pill-accent" : "pill-gray"
                }`}
              >
                {hit.is_final ? "قطعی" : "غیرقطعی"}
              </span>
            )}

            {/* Relevance score */}
            <div 
              className="flex items-center gap-1.5"
              title={`امتیاز مرتبط‌بودن: ${scorePercent}%`}
            >
              <div className="w-12 h-2 bg-slate-200 rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all duration-500 ${
                    scorePercent >= 80 
                      ? "bg-accent-500" 
                      : scorePercent >= 60 
                        ? "bg-primary-500" 
                        : "bg-slate-400"
                  }`}
                  style={{ width: `${scorePercent}%` }}
                />
              </div>
              <span className="text-xs font-medium text-slate-400">
                {scorePercent}%
              </span>
            </div>
          </div>
        </div>

        {/* Section label */}
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs text-primary-600 font-medium flex items-center gap-1">
            <DocumentTextIcon className="h-4 w-4" />
            {sectionLabel}
          </span>
          <span className="text-xs text-slate-400">
            | شناسه: {hit.verdict_id}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="px-5 py-4">
        <p className="text-slate-300 text-sm leading-relaxed line-clamp-4">
          {hit.chunk_text || "متنی موجود نیست."}
        </p>
      </div>

      {/* Footer: Tags and Law Articles */}
      <div className="px-5 py-3 border-t border-slate-100 bg-slate-800/30">
        {/* Law articles */}
        {hit.law_articles && hit.law_articles.length > 0 && (
          <div className="mb-2">
            <span className="text-xs text-slate-500 ml-2">مستندات قانونی:</span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {hit.law_articles.slice(0, 5).map((article, i) => (
                <span
                  key={i}
                  className="pill pill-primary"
                >
                  {article}
                </span>
              ))}
              {hit.law_articles.length > 5 && (
                <span className="pill pill-gray">
                  +{hit.law_articles.length - 5} مورد دیگر
                </span>
              )}
            </div>
          </div>
        )}

        {/* Tags */}
        {hit.tags && hit.tags.length > 0 && (
          <div>
            <span className="text-xs text-slate-500 ml-2">برچسب‌ها:</span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {hit.tags.slice(0, 6).map((tag, i) => (
                <span
                  key={i}
                  className="pill pill-gray"
                >
                  {tag}
                </span>
              ))}
              {hit.tags.length > 6 && (
                <span className="pill pill-gray">
                  +{hit.tags.length - 6}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Empty state */}
        {(!hit.law_articles || hit.law_articles.length === 0) &&
         (!hit.tags || hit.tags.length === 0) && (
          <span className="text-xs text-slate-400">
            بدون برچسب و مستند قانونی
          </span>
        )}
      </div>
    </article>
  );
}
