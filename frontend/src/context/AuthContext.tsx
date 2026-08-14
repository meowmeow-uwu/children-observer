import React, { createContext, useContext, useState, useCallback } from "react";
import type { User, Role } from "../types";
import { loginApi, getMeApi, updateMeApi } from "../services/authApi";
import type { UpdateMePayload } from "../services/authApi";
import { cleanupAllConnections } from "../services/webrtc";

interface AuthContextType {
  user: User | null;
  token: string | null;
  /** Đăng nhập thật: gọi POST /api/auth/login + GET /api/auth/me */
  loginWithCredentials: (email: string, password: string) => Promise<boolean>;
  /** Demo mode: tạo fake token theo role, không cần backend */
  login: (role: Role) => Promise<boolean>;
  logout: () => void;
  /** Cập nhật profile: PATCH /api/auth/me (liên kết Telegram chat ID) */
  updateProfile: (data: UpdateMePayload) => Promise<boolean>;
  isAuthenticated: boolean;
  loginError: string | null;
  isLoggingIn: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ---- Helpers ----

const TOKEN_KEY = "safekid_token";
const USER_KEY = "safekid_user";

const persistSession = (token: string, user: User) => {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
};

const clearSession = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

/** Map API profile → User domain type */
const mapApiUserToUser = (apiUser: Awaited<ReturnType<typeof getMeApi>>): User => ({
  id: String(apiUser.id),
  name: apiUser.full_name,
  email: apiUser.email,
  role: "parent", // Backend không trả về role — mặc định parent
});

// ---- Demo users (giữ lại để demo nhanh không cần backend) ----

const DEMO_USERS: Record<Role, User> = {
  parent: {
    id: "user_parent_01",
    name: "Nguyễn Văn A",
    email: "father.nva@gmail.com",
    role: "parent",
    avatarUrl:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuD7E4wQ6ikYUBfwnfT7fG6yICfwaP_MY7y1qmuJBssWDkxnsLliMIZwZ2G8WB3RLuIT8T1KKJg_cDshSa8sDkiZvTIJ25LExQzxiyy_ouxDtNONNakSiewoLikfNQnnPPgRsWXtCG1I05uiMnaEdRlvS8Z0biwcBFMxwvlBOwe2VNNeR8wzzZ29iGuxihuMqCZN9uHQ-zx-75Ja3-pxy7ZF4dBb107nvujxturBP0CAs95_Y39gwWhLD3otz4GxtqNi9mKiLnszV7KV",
  },
  guardian: {
    id: "user_guardian_01",
    name: "Trần Thị B",
    email: "nanny.ttb@gmail.com",
    role: "guardian",
    avatarUrl:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuBCI0FXHpLQfLFj-6UNQcNILtpX4Ajx_iVZ6ArMjZMDlobInLvawDiinSEI1I4aGrVGi411KmsEIXi_HFWgdRRFXimVDuO1VFNikXE0rAYlLvQVvqxFC8kxXeNJYUDyF7q_FCNC8ksbh__0ZzS1sjElTAOMfQcSfTOam24TsQebg6WDKnObDWlL-VSEU69WzQ7U9xhmZYDIWTOd6aYZXOoqVwKbBd2YlDUXwNDK0ypE2CEM5OBRbxCmp728suzlZ_obf1nTO9IDfxjP",
  },
  viewer: {
    id: "user_viewer_01",
    name: "Viewer Guest",
    email: "guest@example.com",
    role: "viewer",
  },
};

// ---- Provider ----

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Hydrate ngay từ localStorage để tránh flash redirect khi F5
  const [user, setUser] = useState<User | null>(() => {
    try {
      const savedUser = localStorage.getItem(USER_KEY);
      return savedUser ? (JSON.parse(savedUser) as User) : null;
    } catch {
      return null;
    }
  });

  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem(TOKEN_KEY);
  });

  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // ---- Task 1.1: loginWithCredentials — gọi POST /api/auth/login ----

  const loginWithCredentials = useCallback(
    async (email: string, password: string): Promise<boolean> => {
      setIsLoggingIn(true);
      setLoginError(null);
      try {
        // Bước 1: Lấy JWT token
        const tokenResp = await loginApi({ email, password });
        const accessToken = tokenResp.access_token;

        // Bước 2: Lấy thông tin profile
        const apiUser = await getMeApi(accessToken);
        const userDetails = mapApiUserToUser(apiUser);

        setToken(accessToken);
        setUser(userDetails);
        persistSession(accessToken, userDetails);
        return true;
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Đăng nhập thất bại. Vui lòng thử lại.";
        setLoginError(message);
        return false;
      } finally {
        setIsLoggingIn(false);
      }
    },
    []
  );

  // ---- Demo mode login (không cần backend) ----

  const login = useCallback(async (role: Role): Promise<boolean> => {
    const userDetails = DEMO_USERS[role];
    const demoToken = `demo-jwt-${role}-${Date.now()}`;
    setToken(demoToken);
    setUser(userDetails);
    setLoginError(null);
    persistSession(demoToken, userDetails);
    return true;
  }, []);

  // ---- Logout ----

  const logout = useCallback(() => {
    // Dọn sạch tất cả WebRTC connections
    cleanupAllConnections();
    setToken(null);
    setUser(null);
    setLoginError(null);
    clearSession();
  }, []);

  // ---- Task 1.2: updateProfile — PATCH /api/auth/me ----

  const updateProfile = useCallback(
    async (data: UpdateMePayload): Promise<boolean> => {
      const currentToken = localStorage.getItem(TOKEN_KEY);
      if (!currentToken) return false;
      try {
        const updated = await updateMeApi(currentToken, data);
        const updatedUser = mapApiUserToUser(updated);
        setUser(updatedUser);
        persistSession(currentToken, updatedUser);
        return true;
      } catch {
        return false;
      }
    },
    []
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loginWithCredentials,
        login,
        logout,
        updateProfile,
        isAuthenticated: !!token,
        loginError,
        isLoggingIn,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
