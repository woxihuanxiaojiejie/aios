export type ApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
  detail?: unknown;
};

export type ApiClient = {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body?: unknown): Promise<T>;
  patch<T>(path: string, body?: unknown): Promise<T>;
  delete<T>(path: string): Promise<T>;
};

export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;
  readableMessage: string;

  constructor(params: {
    status: number;
    code: string;
    message: string;
    details?: unknown;
  }) {
    super(params.message);
    this.name = "ApiError";
    this.status = params.status;
    this.code = params.code;
    this.details = params.details;
    this.readableMessage = readableMessage(params.status, params.code, params.message);
  }
}

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export const apiClient: ApiClient = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  patch: (path, body) => request(path, { method: "PATCH", body }),
  delete: (path) => request(path, { method: "DELETE" }),
};

async function request<T>(
  path: string,
  init: { method?: string; body?: unknown } = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: init.method ?? "GET",
      headers: {
        "content-type": "application/json",
      },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    });
  } catch (error) {
    throw new ApiError({
      status: 0,
      code: "network_error",
      message: error instanceof Error ? error.message : "Network request failed",
    });
  }

  const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
  if (!response.ok) {
    throw new ApiError({
      status: response.status,
      code: body?.error?.code ?? codeFromStatus(response.status),
      message: body?.error?.message ?? detailMessage(body?.detail) ?? "Backend request failed",
      details: body?.error?.details ?? body?.detail,
    });
  }
  return body as T;
}

function readableMessage(status: number, code: string, message: string) {
  if (status === 0 || code === "network_error") {
    return "API is unavailable. Check VITE_API_BASE_URL and backend status.";
  }
  if (status === 409 || code === "entity_conflict") {
    return "A matching record already exists.";
  }
  if (status === 422 || code === "validation_error") {
    return `Validation error: ${message}`;
  }
  if (status === 404 || code === "entity_not_found") {
    return "The requested record was not found.";
  }
  return message;
}

function codeFromStatus(status: number) {
  if (status === 422) return "validation_error";
  if (status === 404) return "entity_not_found";
  if (status === 409) return "entity_conflict";
  return "request_failed";
}

function detailMessage(detail: unknown) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown };
    return typeof first.msg === "string" ? first.msg : undefined;
  }
  return undefined;
}
