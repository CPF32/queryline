import type { ConnectionFormSchema, JsonSchemaProperty } from "@/types/contracts";

export type FieldErrors = Record<string, string>;

function isEmpty(value: unknown): boolean {
  return value === undefined || value === null || value === "";
}

function validateProperty(
  key: string,
  prop: JsonSchemaProperty,
  value: unknown,
  required: boolean,
): string | null {
  if (isEmpty(value)) {
    return required ? `${prop.title ?? key} is required` : null;
  }

  const type = prop.type ?? "string";

  if (type === "integer") {
    const n = typeof value === "number" ? value : Number(value);
    if (!Number.isInteger(n)) {
      return `${prop.title ?? key} must be a whole number`;
    }
  }

  if (type === "number") {
    const n = typeof value === "number" ? value : Number(value);
    if (Number.isNaN(n)) {
      return `${prop.title ?? key} must be a number`;
    }
  }

  if (type === "boolean" && typeof value !== "boolean") {
    return `${prop.title ?? key} must be true or false`;
  }

  if (prop.enum && prop.enum.length > 0) {
    const str = String(value);
    if (!prop.enum.includes(str)) {
      return `${prop.title ?? key} must be one of: ${prop.enum.join(", ")}`;
    }
  }

  return null;
}

/** Client-side validation against adapter-provided JSON Schema subset. */
export function validateConnectionConfig(
  schema: ConnectionFormSchema,
  values: Record<string, unknown>,
): FieldErrors {
  const errors: FieldErrors = {};
  const required = new Set(schema.required ?? []);

  for (const [key, prop] of Object.entries(schema.properties ?? {})) {
    const err = validateProperty(key, prop, values[key], required.has(key));
    if (err) errors[key] = err;
  }

  return errors;
}

export function hasValidationErrors(errors: FieldErrors): boolean {
  return Object.keys(errors).length > 0;
}

/** Apply schema defaults to empty values. */
export function applySchemaDefaults(
  schema: ConnectionFormSchema,
  values: Record<string, unknown>,
): Record<string, unknown> {
  const next = { ...values };
  for (const [key, prop] of Object.entries(schema.properties ?? {})) {
    if (isEmpty(next[key]) && prop.default !== undefined) {
      next[key] = prop.default;
    }
  }
  return next;
}

/** Masked password sentinel returned by API for unchanged secrets. */
export const MASKED_PASSWORD = "********";

export function isMaskedPassword(value: unknown): boolean {
  return value === MASKED_PASSWORD;
}
