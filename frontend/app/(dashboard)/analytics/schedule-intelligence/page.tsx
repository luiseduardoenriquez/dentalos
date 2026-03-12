"use client";

/**
 * Schedule intelligence analytics page.
 *
 * Wrapper page that renders the existing ScheduleIntelligencePanel component
 * within the analytics layout. The panel fetches its own data from
 * GET /analytics/schedule-intelligence.
 */

import { ScheduleIntelligencePanel } from "@/components/schedule-intelligence-panel";

export default function ScheduleIntelligencePage() {
  return (
    <div className="max-w-3xl">
      <ScheduleIntelligencePanel />
    </div>
  );
}
