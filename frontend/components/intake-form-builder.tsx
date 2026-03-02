"use client";

/**
 * IntakeFormBuilder — Dynamic field renderer for intake form templates.
 *
 * Renders a list of field definitions (stored as JSONB) into actual form inputs.
 * Supports: text, email, phone, date, select, multiselect, checkbox, textarea.
 *
 * Usage:
 *   <IntakeFormBuilder fields={config.fields} values={values} onChange={setValues} />
 */

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export type FieldType =
  | "text"
  | "email"
  | "phone"
  | "date"
  | "select"
  | "multiselect"
  | "checkbox"
  | "textarea";

export interface IntakeFieldDef {
  key: string;
  label: string;
  type: FieldType;
  required: boolean;
  options?: string[];
  placeholder?: string;
}

export interface IntakeFieldValue {
  key: string;
  value: string;
}

interface IntakeFormBuilderProps {
  fields: IntakeFieldDef[];
  values: IntakeFieldValue[];
  onChange: (values: IntakeFieldValue[]) => void;
  readOnly?: boolean;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getValue(values: IntakeFieldValue[], key: string): string {
  return values.find((v) => v.key === key)?.value ?? "";
}

function setValue(
  current: IntakeFieldValue[],
  key: string,
  value: string,
): IntakeFieldValue[] {
  const existing = current.find((v) => v.key === key);
  if (existing) {
    return current.map((v) => (v.key === key ? { ...v, value } : v));
  }
  return [...current, { key, value }];
}

// ─── Individual field renderers ───────────────────────────────────────────────

function TextField({
  field,
  value,
  onChange,
  readOnly,
  inputType = "text",
}: {
  field: IntakeFieldDef;
  value: string;
  onChange: (v: string) => void;
  readOnly?: boolean;
  inputType?: React.HTMLInputTypeAttribute;
}) {
  return (
    <Input
      id={field.key}
      type={inputType}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={field.placeholder}
      required={field.required}
      readOnly={readOnly}
      className={readOnly ? "cursor-default bg-[hsl(var(--muted))]" : ""}
    />
  );
}

function TextareaField({
  field,
  value,
  onChange,
  readOnly,
}: {
  field: IntakeFieldDef;
  value: string;
  onChange: (v: string) => void;
  readOnly?: boolean;
}) {
  return (
    <textarea
      id={field.key}
      rows={3}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={field.placeholder}
      required={field.required}
      readOnly={readOnly}
      className={cn(
        "flex w-full rounded-md border border-[hsl(var(--border))] bg-transparent px-3 py-2 text-sm",
        "placeholder:text-[hsl(var(--muted-foreground))]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
        "disabled:cursor-not-allowed disabled:opacity-50 resize-none",
        readOnly && "cursor-default bg-[hsl(var(--muted))]",
      )}
    />
  );
}

function SelectField({
  field,
  value,
  onChange,
  readOnly,
}: {
  field: IntakeFieldDef;
  value: string;
  onChange: (v: string) => void;
  readOnly?: boolean;
}) {
  if (!field.options || field.options.length === 0) return null;

  return (
    <Select
      value={value}
      onValueChange={onChange}
      disabled={readOnly}
    >
      <SelectTrigger id={field.key}>
        <SelectValue placeholder={field.placeholder ?? "Seleccionar..."} />
      </SelectTrigger>
      <SelectContent>
        {field.options.map((opt) => (
          <SelectItem key={opt} value={opt}>
            {opt}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function MultiselectField({
  field,
  value,
  onChange,
  readOnly,
}: {
  field: IntakeFieldDef;
  value: string;
  onChange: (v: string) => void;
  readOnly?: boolean;
}) {
  const selected = value ? value.split(",").map((v) => v.trim()) : [];

  function toggle(option: string) {
    if (readOnly) return;
    const isSelected = selected.includes(option);
    const next = isSelected
      ? selected.filter((s) => s !== option)
      : [...selected, option];
    onChange(next.join(", "));
  }

  if (!field.options || field.options.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {field.options.map((opt) => {
        const isActive = selected.includes(opt);
        return (
          <button
            key={opt}
            type="button"
            onClick={() => toggle(opt)}
            disabled={readOnly}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              isActive
                ? "border-primary-600 bg-primary-600 text-white"
                : "border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:border-primary-600 hover:text-primary-600",
              readOnly && "cursor-default opacity-70",
            )}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

function CheckboxField({
  field,
  value,
  onChange,
  readOnly,
}: {
  field: IntakeFieldDef;
  value: string;
  onChange: (v: string) => void;
  readOnly?: boolean;
}) {
  const checked = value === "true";

  return (
    <div className="flex items-center gap-2">
      <input
        id={field.key}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked ? "true" : "false")}
        disabled={readOnly}
        className="h-4 w-4 rounded border-[hsl(var(--border))] accent-primary-600"
      />
      <label
        htmlFor={field.key}
        className="text-sm text-foreground cursor-pointer"
      >
        {field.placeholder ?? field.label}
      </label>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function IntakeFormBuilder({
  fields,
  values,
  onChange,
  readOnly = false,
}: IntakeFormBuilderProps) {
  function handleFieldChange(key: string, value: string) {
    onChange(setValue(values, key, value));
  }

  return (
    <div className="space-y-4">
      {fields.map((field) => {
        const currentValue = getValue(values, field.key);

        return (
          <div key={field.key} className="space-y-1">
            {field.type !== "checkbox" && (
              <Label htmlFor={field.key}>
                {field.label}
                {field.required && (
                  <span className="text-destructive ml-0.5">*</span>
                )}
              </Label>
            )}

            {field.type === "text" && (
              <TextField
                field={field}
                value={currentValue}
                onChange={(v) => handleFieldChange(field.key, v)}
                readOnly={readOnly}
                inputType="text"
              />
            )}
            {field.type === "email" && (
              <TextField
                field={field}
                value={currentValue}
                onChange={(v) => handleFieldChange(field.key, v)}
                readOnly={readOnly}
                inputType="email"
              />
            )}
            {field.type === "phone" && (
              <TextField
                field={field}
                value={currentValue}
                onChange={(v) => handleFieldChange(field.key, v)}
                readOnly={readOnly}
                inputType="tel"
              />
            )}
            {field.type === "date" && (
              <TextField
                field={field}
                value={currentValue}
                onChange={(v) => handleFieldChange(field.key, v)}
                readOnly={readOnly}
                inputType="date"
              />
            )}
            {field.type === "textarea" && (
              <TextareaField
                field={field}
                value={currentValue}
                onChange={(v) => handleFieldChange(field.key, v)}
                readOnly={readOnly}
              />
            )}
            {field.type === "select" && (
              <SelectField
                field={field}
                value={currentValue}
                onChange={(v) => handleFieldChange(field.key, v)}
                readOnly={readOnly}
              />
            )}
            {field.type === "multiselect" && (
              <MultiselectField
                field={field}
                value={currentValue}
                onChange={(v) => handleFieldChange(field.key, v)}
                readOnly={readOnly}
              />
            )}
            {field.type === "checkbox" && (
              <CheckboxField
                field={field}
                value={currentValue}
                onChange={(v) => handleFieldChange(field.key, v)}
                readOnly={readOnly}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
