const STORAGE_KEYS = {
  JWT_TOKEN: 'ims-api-tester:jwt-token',
  ENVIRONMENT: 'ims-api-tester:environment',
  THEME: 'ims-api-tester:theme',
  REQUEST_HISTORY: 'ims-api-tester:request-history',
  SIDEBAR_COLLAPSED: 'ims-api-tester:sidebar-collapsed',
} as const;

// SECURITY (Finding 10): the JWT is NOT persisted to localStorage, where any
// XSS on this origin could read it. It is held only in memory for the lifetime
// of the page. Trade-off: the token does not survive a page reload, so the user
// re-authenticates after a refresh. For a customer-facing app, move token
// storage to an HttpOnly, Secure cookie set by the backend instead.
let inMemoryToken: string | null = null;

export function getStoredToken(): string | null {
  return inMemoryToken;
}

export function setStoredToken(token: string): void {
  inMemoryToken = token;
  // Defensively purge any token previously persisted to localStorage.
  localStorage.removeItem(STORAGE_KEYS.JWT_TOKEN);
}

export function clearStoredToken(): void {
  inMemoryToken = null;
  localStorage.removeItem(STORAGE_KEYS.JWT_TOKEN);
}

export function getStoredEnvironment(): string | null {
  return localStorage.getItem(STORAGE_KEYS.ENVIRONMENT);
}

export function setStoredEnvironment(envId: string): void {
  localStorage.setItem(STORAGE_KEYS.ENVIRONMENT, envId);
}

export function getStoredTheme(): 'dark' | 'light' | null {
  return localStorage.getItem(STORAGE_KEYS.THEME) as 'dark' | 'light' | null;
}

export function setStoredTheme(theme: 'dark' | 'light'): void {
  localStorage.setItem(STORAGE_KEYS.THEME, theme);
}

export function getSidebarCollapsed(): boolean {
  return localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED) === 'true';
}

export function setSidebarCollapsed(collapsed: boolean): void {
  localStorage.setItem(STORAGE_KEYS.SIDEBAR_COLLAPSED, String(collapsed));
}

export { STORAGE_KEYS };
