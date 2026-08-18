/**
 * authApi.ts — Service layer cho Authentication domain
 * Theo đặc tả: module_backend_infra/api_and_mqtt_specification.md
 *
 * Endpoints:
 *   POST /api/auth/login  → { access_token, token_type }
 *   GET  /api/auth/me     → UserProfile
 *   PATCH /api/auth/me    → UserProfile (cập nhật tên, telegram_chat_id)
 */

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8007/api";

// ---- Types ----

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}

export interface UserProfileApi {
  id: number;
  email: string;
  full_name: string;
  phone?: string;
  telegram_chat_id?: number | null;
  created_at?: string;
}

export interface UpdateMePayload {
  full_name?: string;
  telegram_chat_id?: number | null;
}

// ---- Auth Error ----

export class AuthApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
  }
}

// ---- Internal helper ----

async function authRequest<T>(
  path: string,
  init?: RequestInit,
  token?: string
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // ignore parse failure
    }
    throw new AuthApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

// ---- Task 1.1: POST /api/auth/login ----

/**
 * Đăng nhập bằng email + password.
 * Trả về JWT access_token.
 */
export const loginApi = async (payload: LoginPayload): Promise<TokenResponse> => {
  return authRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
};

// ---- POST /api/auth/register ----

export interface RegisterPayload {
  email: string;
  password: string;
}

/**
 * Đăng ký tài khoản mới.
 * Trả về UserProfile (id, email).
 */
export const registerApi = async (payload: RegisterPayload): Promise<UserProfileApi> => {
  return authRequest<UserProfileApi>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
};

// ---- Task 1.1: GET /api/auth/me ----

/**
 * Lấy thông tin profile của người dùng hiện tại.
 * Yêu cầu Bearer token hợp lệ.
 */
export const getMeApi = async (token: string): Promise<UserProfileApi> => {
  return authRequest<UserProfileApi>("/auth/me", { method: "GET" }, token);
};

// ---- Task 1.2: PATCH /api/auth/me ----

/**
 * Cập nhật thông tin profile (tên, telegram_chat_id để nhận cảnh báo qua Telegram).
 * Theo task 1.2: liên kết bot Telegram nhận cảnh báo.
 */
export const updateMeApi = async (
  token: string,
  data: UpdateMePayload
): Promise<UserProfileApi> => {
  return authRequest<UserProfileApi>(
    "/auth/me",
    {
      method: "PATCH",
      body: JSON.stringify(data),
    },
    token
  );
};
