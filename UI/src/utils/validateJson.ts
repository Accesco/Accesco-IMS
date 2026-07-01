export interface JsonValidationResult {
  valid: boolean;
  error?: string;
  parsed?: unknown;
}

export function validateJson(value: string): JsonValidationResult {
  if (!value.trim()) {
    return { valid: true, parsed: undefined };
  }

  try {
    const parsed = JSON.parse(value);
    return { valid: true, parsed };
  } catch (e) {
    const error = e instanceof Error ? e.message : 'Invalid JSON';
    return { valid: false, error };
  }
}
