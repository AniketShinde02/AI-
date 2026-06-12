import { logger } from "./logger";

/**
 * Centralized API Client
 * - Single source of truth for all external calls.
 * - Supports request cancellation via AbortController.
 * - Handles base URL, common headers, and error parsing.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

export type ApiRequestConfig = RequestInit & {
  params?: Record<string, string>;
};

export class ApiError extends Error {
  constructor(public status: number, message: string, public data?: any) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(endpoint: string, config: ApiRequestConfig = {}): Promise<T> {
  const { params, ...customConfig } = config;
  
  // Build URL with query parameters
  const baseUrl = BASE_URL || (typeof window !== 'undefined' ? window.location.origin : '');
  const url = new URL(endpoint, baseUrl);
  if (params) {
    Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
  }

  const headers = {
    "Content-Type": "application/json",
    ...customConfig.headers,
  };

  const finalConfig: RequestInit = {
    ...customConfig,
    headers,
  };

  logger.api(finalConfig.method || "GET", url.toString(), undefined, customConfig.body);

  const response = await fetch(url.toString(), finalConfig);

  if (!response.ok) {
    // Attempt to parse error message from JSON body
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = null;
    }
    
    logger.error(`API Failure: ${url.toString()}`, { status: response.status, errorData });

    throw new ApiError(
      response.status, 
      errorData?.detail || errorData?.message || `HTTP Error: ${response.status}`,
      errorData
    );
  }

  logger.info(`API Success: ${url.toString()}`, { status: response.status });

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const apiClient = {
  get: <T>(endpoint: string, config?: ApiRequestConfig) => 
    request<T>(endpoint, { ...config, method: "GET" }),
    
  post: <T>(endpoint: string, data?: any, config?: ApiRequestConfig) => 
    request<T>(endpoint, { ...config, method: "POST", body: JSON.stringify(data) }),
    
  put: <T>(endpoint: string, data?: any, config?: ApiRequestConfig) => 
    request<T>(endpoint, { ...config, method: "PUT", body: JSON.stringify(data) }),
    
  patch: <T>(endpoint: string, data?: any, config?: ApiRequestConfig) => 
    request<T>(endpoint, { ...config, method: "PATCH", body: JSON.stringify(data) }),
    
  delete: <T>(endpoint: string, config?: ApiRequestConfig) => 
    request<T>(endpoint, { ...config, method: "DELETE" }),
};
