const STORAGE_KEYS = {
  JWT_TOKEN: 'ims-api-tester:jwt-token',
  ENVIRONMENT: 'ims-api-tester:environment',
  THEME: 'ims-api-tester:theme',
  REQUEST_HISTORY: 'ims-api-tester:request-history',
  SIDEBAR_COLLAPSED: 'ims-api-tester:sidebar-collapsed',
} as const;

export function getStoredToken(): string | null {
  return localStorage.getItem(STORAGE_KEYS.JWT_TOKEN);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(STORAGE_KEYS.JWT_TOKEN, token);
}

export function clearStoredToken(): void {
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
