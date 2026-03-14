"use client";

import * as React from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/agenda/calendar";
import { AppointmentCreateModal } from "@/components/agenda/appointment-create-modal";
import { AppointmentDetailModal } from "@/components/agenda/appointment-detail-modal";
import type { CalendarSlot } from "@/lib/hooks/use-appointments";

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Agenda main page (FE-AG-01).
 *
 * Renders the full-featured calendar with day/week/month views.
 * Manages modal state for:
 * - Creating a new appointment (AppointmentCreateModal)
 * - Viewing appointment details (AppointmentDetailModal)
 *
 * The Calendar component emits events for slot and appointment clicks;
 * this page translates those into modal open/close state.
 */
export default function AgendaPage() {
  // ─── Create modal state ─────────────────────────────────────────────
  const [create_open, set_create_open] = React.useState(false);
  const [pre_fill_start_time, set_pre_fill_start_time] = React.useState<
    string | undefined
  >(undefined);

  // ─── Detail modal state ─────────────────────────────────────────────
  const [detail_open, set_detail_open] = React.useState(false);
  const [selected_appointment_id, set_selected_appointment_id] = React.useState<
    string | null
  >(null);

  // ─── Event handlers ──────────────────────────────────────────────────

  function handle_appointment_click(slot: CalendarSlot) {
    set_selected_appointment_id(slot.id);
    set_detail_open(true);
  }

  function handle_slot_click(iso_datetime: string) {
    set_pre_fill_start_time(iso_datetime.slice(0, 16)); // datetime-local format
    set_create_open(true);
  }

  function handle_create_click() {
    set_pre_fill_start_time(undefined);
    set_create_open(true);
  }

  function handle_create_close() {
    set_create_open(false);
    set_pre_fill_start_time(undefined);
  }

  function handle_detail_close() {
    set_detail_open(false);
    set_selected_appointment_id(null);
  }

  return (
    <div className="flex flex-col h-full gap-4 px-6">
      {/* FAB for mobile — shown only on small screens */}
      <Button
        onClick={handle_create_click}
        className="md:hidden fixed bottom-6 right-6 z-20 h-14 w-14 rounded-full shadow-lg p-0"
        size="icon"
        aria-label="Nueva cita"
      >
        <Plus className="h-6 w-6" />
      </Button>

      {/* ─── Calendar ─────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden">
        <Calendar
          onAppointmentClick={handle_appointment_click}
          onSlotClick={handle_slot_click}
          onCreateClick={handle_create_click}
          className="h-full"
        />
      </div>

      {/* ─── Create Modal ─────────────────────────────────────────────── */}
      <AppointmentCreateModal
        open={create_open}
        onOpenChange={(v) => {
          if (!v) handle_create_close();
        }}
        defaultDate={pre_fill_start_time}
      />

      {/* ─── Detail Modal ─────────────────────────────────────────────── */}
      <AppointmentDetailModal
        appointmentId={selected_appointment_id}
        open={detail_open}
        onOpenChange={(v) => {
          if (!v) handle_detail_close();
        }}
      />
    </div>
  );
}
