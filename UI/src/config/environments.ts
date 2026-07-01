import type { Environment } from '../types/environment';

export const environments: Environment[] = [
  {
    id: 'local',
    name: 'Local',
    baseUrl: 'http://127.0.0.1:8000/api/v1',
    description: 'Local development server',
  },
  {
    id: 'development',
    name: 'Development',
    baseUrl: 'http://127.0.0.1:8000/api/v1',
    description: 'Development server (pointing to local for now)',
  },
  {
    id: 'staging',
    name: 'Staging',
    baseUrl: 'http://127.0.0.1:8000/api/v1',
    description: 'Staging server (pointing to local for now)',
  },
];

export const DEFAULT_ENVIRONMENT_ID = 'local';
