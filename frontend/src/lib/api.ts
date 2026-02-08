/**
 * API Client Library for the Financial Intelligence Swarm backend.
 *
 * Features:
 * - Type-safe request/response handling
 * - Environment-based API URL configuration
 * - Request/response logging for debugging
 * - Graceful error handling with typed errors
 * - Streaming support for investigation endpoint
 */

import type {
  ApiError,
  IngestRequest,
  IngestResponse,
  InvestigateRequest,
  ListTransactionsParams,
  ListTransactionsResponse,
  OverrideRequest,
  OverrideResponse,
  TransactionDetail,
  HealthResponse,
  Transaction,
  StreamData,
  SARReport,
} from "./types";

// ============================================================================
// Configuration
// ============================================================================

/**
 * API base URL from environment or default to localhost.
 * Set NEXT_PUBLIC_API_URL in .env.local for different environments.
 */
const rawApiUrl =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : process.env.API_URL || "http://localhost:8000";

/**
 * Ensure the API URL has a protocol. If missing, default to https://
 */
const API_BASE_URL = rawApiUrl.match(/^https?:\/\//)
  ? rawApiUrl
  : `https://${rawApiUrl}`;

/**
 * Enable debug logging (can be set via environment variable)
 */
const DEBUG_LOGGING =
  process.env.NEXT_PUBLIC_API_DEBUG === "true" ||
  process.env.NODE_ENV === "development";

// ============================================================================
// Logging Utilities
// ============================================================================

interface LogContext {
  method: string;
  url: string;
  body?: unknown;
  response?: unknown;
  error?: unknown;
  duration?: number;
}

function logRequest(context: LogContext): void {
  if (!DEBUG_LOGGING) return;

  const timestamp = new Date().toISOString();
  console.group(`[API ${context.method}] ${context.url}`);
  console.log(`Timestamp: ${timestamp}`);
  if (context.body) {
    console.log("Request Body:", context.body);
  }
  console.groupEnd();
}

function logResponse(context: LogContext): void {
  if (!DEBUG_LOGGING) return;

  console.group(`[API Response] ${context.method} ${context.url}`);
  console.log(`Duration: ${context.duration}ms`);
  console.log("Response:", context.response);
  console.groupEnd();
}

function logError(context: LogContext): void {
  console.group(`[API Error] ${context.method} ${context.url}`);
  console.error("Error:", context.error);
  if (context.body) {
    console.log("Request Body:", context.body);
  }
  console.groupEnd();
}

// ============================================================================
// Error Handling
// ============================================================================

/**
 * Custom error class for API errors with typed response data.
 */
export class FisApiError extends Error {
  public readonly status: number;
  public readonly detail: string;
  public readonly code?: string;
  public originalError?: Error;

  constructor(message: string, status: number, detail?: string, code?: string) {
    super(message);
    this.name = "FisApiError";
    this.status = status;
    this.detail = detail || message;
    this.code = code;
  }

  static fromResponse(response: Response, detail?: string): FisApiError {
    return new FisApiError(
      detail || response.statusText || `HTTP ${response.status}`,
      response.status,
      detail
    );
  }

  static fromError(error: Error, context?: string): FisApiError {
    const apiError = new FisApiError(
      context ? `${context}: ${error.message}` : error.message,
      0,
      error.message,
      "NETWORK_ERROR"
    );
    apiError.originalError = error;
    return apiError;
  }

  toApiError(): ApiError {
    return {
      detail: this.detail,
      status: this.status,
      code: this.code,
    };
  }
}

/**
 * Parse error response body to extract detail message.
 */
async function parseErrorResponse(response: Response): Promise<string> {
  try {
    const contentType = response.headers.get("content-type");
    if (contentType?.includes("application/json")) {
      const data = await response.json();
      return data.detail || data.message || JSON.stringify(data);
    }
    return await response.text();
  } catch {
    return response.statusText || `HTTP Error ${response.status}`;
  }
}

// ============================================================================
// HTTP Client
// ============================================================================

interface RequestOptions {
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

/**
 * Make an HTTP request to the API with logging and error handling.
 */
async function request<T>(
  endpoint: string,
  options: RequestOptions
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const startTime = Date.now();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...options.headers,
  };

  const fetchOptions: RequestInit = {
    method: options.method,
    headers,
    signal: options.signal,
  };

  if (options.body !== undefined) {
    fetchOptions.body = JSON.stringify(options.body);
  }

  logRequest({ method: options.method, url, body: options.body });

  try {
    const response = await fetch(url, fetchOptions);
    const duration = Date.now() - startTime;

    if (!response.ok) {
      const detail = await parseErrorResponse(response);
      logError({
        method: options.method,
        url,
        body: options.body,
        error: { status: response.status, detail },
      });
      throw FisApiError.fromResponse(response, detail);
    }

    const data = (await response.json()) as T;
    logResponse({ method: options.method, url, response: data, duration });

    return data;
  } catch (error) {
    if (error instanceof FisApiError) {
      throw error;
    }

    const apiError = FisApiError.fromError(
      error instanceof Error ? error : new Error(String(error)),
      `Request to ${endpoint} failed`
    );

    logError({
      method: options.method,
      url,
      body: options.body,
      error: apiError,
    });

    throw apiError;
  }
}

// ============================================================================
// API Client Functions
// ============================================================================

/**
 * Health check endpoint.
 * GET /
 */
export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request<HealthResponse>("/", {
    method: "GET",
    signal,
  });
}

/**
 * Ingest an ISO 20022 XML message.
 * POST /ingest
 *
 * @param data - The XML content and message type
 * @returns The parsed transaction with UETR
 *
 * @example
 * ```ts
 * const result = await ingestTransaction({
 *   xml_content: '<Document>...</Document>',
 *   message_type: 'pacs.008'
 * });
 * console.log(`Ingested transaction: ${result.uetr}`);
 * ```
 */
export async function ingestTransaction(
  data: IngestRequest,
  signal?: AbortSignal
): Promise<IngestResponse> {
  return request<IngestResponse>("/ingest", {
    method: "POST",
    body: data,
    signal,
  });
}

/**
 * List all ingested transactions.
 * GET /transactions
 *
 * @param params - Optional filtering and pagination parameters
 * @returns List of transactions with total count
 *
 * @example
 * ```ts
 * const { transactions, total } = await listTransactions({
 *   status: 'pending',
 *   limit: 20
 * });
 * ```
 */
export async function listTransactions(
  params?: ListTransactionsParams,
  signal?: AbortSignal
): Promise<ListTransactionsResponse> {
  const searchParams = new URLSearchParams();

  if (params?.status) {
    searchParams.append("status", params.status);
  }
  if (params?.limit !== undefined) {
    searchParams.append("limit", params.limit.toString());
  }

  const queryString = searchParams.toString();
  const endpoint = queryString ? `/transactions?${queryString}` : "/transactions";

  const response = await request<{
    transactions: Array<{
      uetr: string;
      debtor: string;
      creditor: string;
      amount: number;
      currency: string;
      status: string;
      risk_level: string | null;
      created_at: string;
    }>;
    total: number;
  }>(endpoint, {
    method: "GET",
    signal,
  });

  // Transform snake_case to camelCase
  return {
    transactions: response.transactions.map((tx) => ({
      uetr: tx.uetr,
      debtor: tx.debtor,
      creditor: tx.creditor,
      amount: tx.amount,
      currency: tx.currency,
      status: tx.status as Transaction["status"],
      riskLevel: tx.risk_level as Transaction["riskLevel"],
      createdAt: tx.created_at,
    })),
    total: response.total,
  };
}

/**
 * Get a specific transaction by UETR.
 * GET /transactions/{uetr}
 *
 * @param uetr - The unique end-to-end transaction reference
 * @returns Detailed transaction information
 *
 * @example
 * ```ts
 * const tx = await getTransaction('550e8400-e29b-41d4-a716-446655440000');
 * console.log(`Status: ${tx.status}, Risk: ${tx.risk_level}`);
 * ```
 */
export async function getTransaction(
  uetr: string,
  signal?: AbortSignal
): Promise<TransactionDetail> {
  return request<TransactionDetail>(`/transactions/${encodeURIComponent(uetr)}`, {
    method: "GET",
    signal,
  });
}

/**
 * Start an investigation on a transaction.
 * POST /investigate
 *
 * Returns a streaming response using Vercel AI SDK Data Stream Protocol.
 *
 * @param data - The UETR to investigate
 * @returns Async iterator of stream events
 *
 * @example
 * ```ts
 * for await (const event of investigateTransaction({ uetr: '...' })) {
 *   if (event.type === 'verdict') {
 *     console.log('Final verdict:', event.verdict);
 *   }
 * }
 * ```
 */
export async function* investigateTransaction(
  data: InvestigateRequest,
  signal?: AbortSignal
): AsyncGenerator<StreamData | { type: "text"; content: string }> {
  const url = `${API_BASE_URL}/investigate`;

  logRequest({ method: "POST", url, body: data });

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(data),
    signal,
  });

  if (!response.ok) {
    const detail = await parseErrorResponse(response);
    throw FisApiError.fromResponse(response, detail);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new FisApiError(
      "No response body available for streaming",
      0,
      "No response body",
      "STREAM_ERROR"
    );
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) continue;

        // Parse Vercel AI SDK Data Stream Protocol
        // Format: TYPE:JSON_DATA
        const colonIndex = line.indexOf(":");
        if (colonIndex === -1) continue;

        const type = line.substring(0, colonIndex);
        const rawData = line.substring(colonIndex + 1);

        try {
          switch (type) {
            case "0": {
              // Text content
              const text = JSON.parse(rawData);
              yield { type: "text" as const, content: text };
              break;
            }
            case "d": {
              // Structured data
              const parsed = JSON.parse(rawData) as StreamData;
              if (DEBUG_LOGGING) {
                console.log("[Stream Data]", parsed);
              }
              yield parsed;
              break;
            }
            case "b": {
              // Tool call (log but don't yield)
              if (DEBUG_LOGGING) {
                console.log("[Stream Tool]", JSON.parse(rawData));
              }
              break;
            }
            case "e": {
              // Error
              const error = JSON.parse(rawData);
              yield { type: "error" as const, message: error.message || String(error) };
              break;
            }
            default: {
              if (DEBUG_LOGGING) {
                console.log(`[Stream Unknown ${type}]`, rawData);
              }
            }
          }
        } catch (parseError) {
          if (DEBUG_LOGGING) {
            console.error("Failed to parse stream data:", parseError, { line });
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Start an investigation and collect all events into an array.
 * Convenience wrapper around investigateTransaction for non-streaming usage.
 *
 * @param data - The UETR to investigate
 * @returns All stream events collected
 */
export async function investigateTransactionComplete(
  data: InvestigateRequest,
  signal?: AbortSignal
): Promise<Array<StreamData | { type: "text"; content: string }>> {
  const events: Array<StreamData | { type: "text"; content: string }> = [];

  for await (const event of investigateTransaction(data, signal)) {
    events.push(event);
  }

  return events;
}

/**
 * Submit a human override for a transaction.
 * POST /override/{uetr}
 *
 * @param uetr - The transaction UETR
 * @param data - The override decision and reason
 * @returns Confirmation with override details
 *
 * @example
 * ```ts
 * const result = await submitOverride('550e8400-...', {
 *   action: 'approve',
 *   reason: 'Verified legitimate business transaction'
 * });
 * ```
 */
export async function submitOverride(
  uetr: string,
  data: OverrideRequest,
  signal?: AbortSignal
): Promise<OverrideResponse> {
  return request<OverrideResponse>(`/override/${encodeURIComponent(uetr)}`, {
    method: "POST",
    body: {
      action: data.action,
      reason: data.reason || "",
    },
    signal,
  });
}

/**
 * Generate a Suspicious Activity Report (SAR) for a transaction.
 * POST /generate-sar/{uetr}
 *
 * @param uetr - The transaction UETR
 * @returns SAR document with transaction details and investigation findings
 */
export async function generateSAR(
  uetr: string,
  signal?: AbortSignal
): Promise<SARReport> {
  return request<SARReport>(`/generate-sar/${encodeURIComponent(uetr)}`, {
    method: "POST",
    signal,
  });
}

/**
 * Generate 5 synthetic transactions for testing.
 * POST /generate-synthetic-data
 * 
 * @returns The generated transactions
 */
export async function generateSyntheticData(
  signal?: AbortSignal
): Promise<{ generated: number; transactions: Record<string, unknown>[] }> {
  return request<{ generated: number; transactions: Record<string, unknown>[] }>("/generate-synthetic-data", {
    method: "POST",
    signal,
  });
}

/**
 * Clear all transactions.
 * POST /clear-data
 */
export async function clearData(
  signal?: AbortSignal
): Promise<{ success: boolean; message: string }> {
  return request<{ success: boolean; message: string }>("/clear-data", {
    method: "POST",
    signal,
  });
}

/**
 * Annex IV documentation response type
 */
export interface AnnexIVResponse {
  uetr: string;
  generated_at: string;
  system_description: {
    name: string;
    type: string;
    version: string;
    agents: Array<{ name: string; role: string }>;
  };
  intended_purpose: string;
  technical_architecture: {
    orchestration: string;
    graph_database: string;
    vector_database: string;
    behavioral_memory: string;
    llm_provider: string;
  };
  risk_management: string[];
  human_oversight: {
    required: boolean;
    description: string;
  };
  transaction_record: {
    uetr: string;
    originator: string;
    beneficiary: string;
    amount: string;
    risk_level: string;
    verdict: string;
    confidence_score: number;
  };
}

/**
 * Get Annex IV Technical Documentation for a transaction.
 * GET /annex-iv/{uetr}
 *
 * @param uetr - The transaction UETR
 * @returns Annex IV documentation structure for EU AI Act compliance
 */
export async function getAnnexIV(
  uetr: string,
  signal?: AbortSignal
): Promise<AnnexIVResponse> {
  return request<AnnexIVResponse>(`/annex-iv/${encodeURIComponent(uetr)}`, {
    method: "GET",
    signal,
  });
}

/**
 * Get the URL for downloading SAR PDF
 * @param uetr - The transaction UETR
 * @returns URL string for downloading the PDF
 */
export function getSarPdfUrl(uetr: string): string {
  return `${API_BASE_URL}/generate-sar-pdf/${encodeURIComponent(uetr)}`;
}

/**
 * Get the URL for downloading Annex IV PDF
 * @param uetr - The transaction UETR
 * @returns URL string for downloading the PDF
 */
export function getAnnexIvPdfUrl(uetr: string): string {
  return `${API_BASE_URL}/annex-iv-pdf/${encodeURIComponent(uetr)}`;
}

// ============================================================================
// API Client Class (Alternative OOP Interface)
// ============================================================================

/**
 * API Client class for object-oriented usage pattern.
 * Provides the same functionality as the standalone functions.
 *
 * @example
 * ```ts
 * const api = new FisApiClient('http://localhost:8000');
 *
 * // List transactions
 * const { transactions } = await api.listTransactions();
 *
 * // Ingest a new transaction
 * const result = await api.ingest({
 *   xml_content: '<Document>...</Document>',
 *   message_type: 'pacs.008'
 * });
 * ```
 */
export class FisApiClient {
  private baseUrl: string;
  private debug: boolean;

  constructor(baseUrl?: string, options?: { debug?: boolean }) {
    this.baseUrl = baseUrl || API_BASE_URL;
    this.debug = options?.debug ?? DEBUG_LOGGING;
  }

  /**
   * Health check
   */
  async health(signal?: AbortSignal): Promise<HealthResponse> {
    return getHealth(signal);
  }

  /**
   * Ingest ISO 20022 XML
   */
  async ingest(
    data: IngestRequest,
    signal?: AbortSignal
  ): Promise<IngestResponse> {
    return ingestTransaction(data, signal);
  }

  /**
   * List transactions
   */
  async listTransactions(
    params?: ListTransactionsParams,
    signal?: AbortSignal
  ): Promise<ListTransactionsResponse> {
    return listTransactions(params, signal);
  }

  /**
   * Get single transaction
   */
  async getTransaction(
    uetr: string,
    signal?: AbortSignal
  ): Promise<TransactionDetail> {
    return getTransaction(uetr, signal);
  }

  /**
   * Investigate transaction (streaming)
   */
  investigate(
    data: InvestigateRequest,
    signal?: AbortSignal
  ): AsyncGenerator<StreamData | { type: "text"; content: string }> {
    return investigateTransaction(data, signal);
  }

  /**
   * Investigate transaction (complete)
   */
  async investigateComplete(
    data: InvestigateRequest,
    signal?: AbortSignal
  ): Promise<Array<StreamData | { type: "text"; content: string }>> {
    return investigateTransactionComplete(data, signal);
  }

  /**
   * Submit override
   */
  async override(
    uetr: string,
    data: OverrideRequest,
    signal?: AbortSignal
  ): Promise<OverrideResponse> {
    return submitOverride(uetr, data, signal);
  }

  /**
   * Generate SAR
   */
  async generateSAR(
    uetr: string,
    signal?: AbortSignal
  ): Promise<SARReport> {
    return generateSAR(uetr, signal);
  }

  /**
   * Generate synthetic data
   */
  async generateSyntheticData(
    signal?: AbortSignal
  ): Promise<{ generated: number; transactions: Record<string, unknown>[] }> {
    return generateSyntheticData(signal);
  }

  /**
   * Clear all transactions
   */
  async clearData(
    signal?: AbortSignal
  ): Promise<{ success: boolean; message: string }> {
    return clearData(signal);
  }
}

// ============================================================================
// Exports
// ============================================================================

export { API_BASE_URL, DEBUG_LOGGING };

// Default client instance
export const api = new FisApiClient();

// Re-export types for convenience
export type * from "./types";
