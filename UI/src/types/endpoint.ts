export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

export interface ParamDefinition {
  name: string;
  type: 'string' | 'number' | 'boolean';
  required: boolean;
  description?: string;
  defaultValue?: string;
}

export interface Endpoint {
  id: string;
  method: HttpMethod;
  path: string;
  description: string;
  pathParams?: ParamDefinition[];
  queryParams?: ParamDefinition[];
  sampleBody?: Record<string, unknown>;
  requiresAuth: boolean;
}

export interface EndpointModule {
  id: string;
  name: string;
  icon: string;
  description: string;
  endpoints: Endpoint[];
}
