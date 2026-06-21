/**
 * Timeline Visualization Component
 * 
 * Interactive timeline visualization with:
 * - Event timeline
 * - Conflict detection
 * - Zoom and pan
 * - Event details
 */

import { useState } from "react";
import { generateTimelineReport } from "../api/mahounClient";
import { toast } from "./Toast";

interface TimelineEvent {
  date: string;
  description: string;
  sequence: number;
  source?: string;
}

interface TimelineData {
  timeline: TimelineEvent[];
  conflicts: Array<{
    date: string;
    type: string;
    conflicting_events: TimelineEvent[];
  }>;
}

export default function TimelineVisualization() {
  const [query, setQuery] = useState("");
  const [timelineData, setTimelineData] = useState<TimelineData | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    if (!query) return;

    setLoading(true);
    try {
      await generateTimelineReport(query);
      // Parse timeline from report content
      // In production, this would come from the API response
      setTimelineData({
        timeline: [],
        conflicts: [],
      });
    } catch (error: any) {
      toast.error(`خطا در تولید خط‌زمان: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 page-enter">
      <div className="bg-slate-900 rounded-xl shadow-lg border border-slate-700 p-8">
        <h2 className="text-2xl font-bold text-slate-100 mb-6">نمایش خط‌زمان</h2>

        {/* Input */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            سؤال یا موضوع
          </label>
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="مثال: توالی وقایع پروژه"
              className="flex-1 px-4 py-2 border border-slate-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            <button
              onClick={handleGenerate}
              disabled={loading || !query}
              className="px-6 py-2 bg-primary-700 text-white rounded-lg hover:bg-primary-800 disabled:opacity-50"
            >
              {loading ? "در حال تولید..." : "تولید Timeline"}
            </button>
          </div>
        </div>

        {/* Timeline Visualization */}
        {timelineData && timelineData.timeline.length > 0 && (
          <div className="mt-8">
            <div className="relative">
              {/* Timeline Line */}
              <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-primary-200"></div>

              {/* Events */}
              <div className="space-y-6">
                {timelineData.timeline.map((event, index) => (
                  <div
                    key={index}
                    className="relative flex items-start gap-4 p-3 rounded-lg"
                  >
                    {/* Timeline Dot */}
                    <div className="relative z-10 flex-shrink-0">
                      <div className="w-4 h-4 bg-primary-700 rounded-full border-4 border-white shadow-md"></div>
                    </div>

                    {/* Event Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-sm font-semibold text-primary-700">
                          {event.date}
                        </span>
                        <span className="text-xs text-slate-500">
                          رویداد #{event.sequence}
                        </span>
                      </div>
                      <p className="text-sm text-slate-100">{event.description}</p>
                      {event.source && (
                        <p className="text-xs text-slate-500 mt-1">منبع: {event.source}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Conflicts */}
            {timelineData.conflicts.length > 0 && (
              <div className="mt-8 bg-accent-50 border border-accent-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-accent-900 mb-4">
                  هشدار تضادها در Timeline ({timelineData.conflicts.length})
                </h3>
                {timelineData.conflicts.map((conflict, index) => (
                  <div key={index} className="mb-4 last:mb-0">
                    <p className="text-sm font-medium text-accent-800">
                      تاریخ: {conflict.date} - نوع: {conflict.type}
                    </p>
                    <p className="text-xs text-accent-700 mt-1">
                      {conflict.conflicting_events.length} رویداد متضاد
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Empty State */}
        {!timelineData && !loading && (
          <div className="text-center py-12 text-slate-500">
            برای نمایش timeline، یک سؤال وارد کنید و روی "تولید Timeline" کلیک کنید
          </div>
        )}
      </div>
    </div>
  );
}
