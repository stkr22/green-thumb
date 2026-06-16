// Thin fetch wrapper: cookie-based auth (credentials: include) and uniform
// error handling. A 401 anywhere means the session is gone, so we bounce the
// browser to the backend login route, which redirects to Zitadel.

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function loginUrl(): string {
  return `${BASE}/auth/login`;
}

export function logoutUrl(): string {
  return `${BASE}/auth/logout`;
}

export function photoUrl(photoId: string): string {
  return `${BASE}/api/v1/photos/${photoId}`;
}

// Small downscaled variant for grids and cards; far fewer bytes than the
// display image served by photoUrl.
export function thumbnailUrl(photoId: string): string {
  return `${BASE}/api/v1/photos/${photoId}/thumb`;
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === 'string') return body.detail;
  } catch {
    // Non-JSON error body; fall through to the status text.
  }
  return `${response.status} ${response.statusText}`;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { credentials: 'include', ...init });
  if (response.status === 401) {
    window.location.assign(loginUrl());
    throw new ApiError(401, 'Not authenticated');
  }
  if (!response.ok) {
    throw new ApiError(response.status, await parseError(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function jsonBody(payload: unknown): RequestInit {
  return { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) };
}
