export function formatJson(value: unknown): string {
  try {
    if (typeof value === 'string') {
      return JSON.stringify(JSON.parse(value), null, 2);
    }
    return JSON.stringify(value, null, 2);
  } catch {
    return typeof value === 'string' ? value : String(value);
  }
}

export function minifyJson(value: string): string {
  try {
    return JSON.stringify(JSON.parse(value));
  } catch {
    return value;
  }
}
