/**
 * MAHOUN API Service
 * 
 * Centralized API configuration and base service class
 */

// Single source of truth for API configuration
export class APIConfig {
  private static instance: APIConfig;
  private readonly baseURL: string;
  private readonly timeout: number;
  
  private constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    this.timeout = Number(import.meta.env.VITE_API_TIMEOUT) || 30000;
  }
  
  public static getInstance(): APIConfig {
    if (!APIConfig.instance) {
      APIConfig.instance = new APIConfig();
    }
    return APIConfig.instance;
  }
  
  public getBaseURL(): string {
    return this.baseURL;
  }
  
  public getTimeout(): number {
    return this.timeout;
  }
}

/**
 * Base API Service Class
 */
export abstract class BaseAPIService {
  protected config: APIConfig;
  
  constructor() {
    this.config = APIConfig.getInstance();
  }
  
  protected async request<T>(
    endpoint: string,
    options: RequestInit & { timeout?: number } = {}
  ): Promise<T> {
    const { timeout = this.config.getTimeout(), ...fetchOptions } = options;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const response = await fetch(`${this.config.getBaseURL()}${endpoint}`, {
        ...fetchOptions,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...fetchOptions.headers,
        },
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }
}