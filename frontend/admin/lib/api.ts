const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://threed-menu-api.onrender.com";

export function resolveMediaUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${API_BASE_URL}${path}`;
}

function extractErrorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object") {
    const data = body as Record<string, unknown>;
    if ("detail" in data) return String(data.detail);

    // DRF validation errors look like { field: ["msg", ...], non_field_errors: [...] }.
    const messages = Object.values(data).flatMap((value) =>
      Array.isArray(value) ? value.map(String) : typeof value === "string" ? [value] : []
    );
    if (messages.length > 0) return messages.join(" ");
  }
  return `So'rov xatosi (${status})`;
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(extractErrorMessage(body, status));
    this.status = status;
    this.body = body;
  }
}

export class AuthenticationError extends ApiError {}

let refreshInFlight: Promise<boolean> | null = null;

function authDebug(message: string, details: Record<string, unknown> = {}) {
  if (process.env.NODE_ENV === "development") {
    console.debug(`[auth] ${message} ${JSON.stringify(details)}`);
  }
}

async function refreshSession(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/refresh/`, {
        method: "POST",
        credentials: "include",
      });
      authDebug("refresh response", { path: "/api/auth/refresh/", status: res.status });
      return res.ok;
    } catch {
      authDebug("refresh response", { path: "/api/auth/refresh/", status: "network_error" });
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  if (window.location.pathname !== "/login") {
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/login";
  }
}

/** Authenticated fetch: the JWT lives in an httpOnly cookie the browser sends
 * automatically. Retries once after a silent refresh on 401, and parses JSON. */
export async function apiFetch<T>(
  path: string,
  options: { method?: string; body?: BodyInit; isForm?: boolean; auth?: boolean; redirectOnAuthFailure?: boolean } = {}
): Promise<T> {
  const { method = "GET", body, isForm = false, auth = true, redirectOnAuthFailure = true } = options;

  const doFetch = () => {
    const headers: Record<string, string> = {};
    if (!isForm && body) headers["Content-Type"] = "application/json";

    return fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body,
      credentials: auth ? "include" : "same-origin",
    });
  };

  let res = await doFetch();
  authDebug("request response", { path, status: res.status, retryAttempted: false });

  if (res.status === 401 && auth) {
    authDebug("refresh attempted", { path, refreshAttempted: true });
    const refreshed = await refreshSession();
    if (refreshed) {
      res = await doFetch();
      authDebug("request response", { path, status: res.status, retryAttempted: true });
    }
  }

  if (res.status === 204) return undefined as T;

  const contentType = res.headers.get("content-type") ?? "";
  const data = contentType.includes("application/json") ? await res.json() : undefined;

  if (res.status === 401 && auth) {
    if (redirectOnAuthFailure) redirectToLogin();
    throw new AuthenticationError(res.status, data);
  }

  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}
