import { environments, DEFAULT_ENVIRONMENT_ID } from '../config/environments';
import type { Environment } from '../types/environment';
import { getStoredEnvironment } from './storage';

export function getCurrentEnvironment(): Environment {
  const storedId = getStoredEnvironment();
  const env = environments.find((e) => e.id === storedId);
  return env ?? environments.find((e) => e.id === DEFAULT_ENVIRONMENT_ID)!;
}

export function getBaseUrl(): string {
  return getCurrentEnvironment().baseUrl;
}

export function getAllEnvironments(): Environment[] {
  return environments;
}
