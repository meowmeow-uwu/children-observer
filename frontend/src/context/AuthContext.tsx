import React, { createContext, useContext, useState, useEffect } from "react";
import type { User, Role } from "../types";

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (role: Role) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const savedToken = localStorage.getItem("safekid_token");
    const savedUser = localStorage.getItem("safekid_user");
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
  }, []);

  const login = async (role: Role): Promise<boolean> => {
    // Simulated authentication process
    let userDetails: User;
    if (role === "parent") {
      userDetails = {
        id: "user_parent_01",
        name: "Nguyễn Văn A",
        email: "father.nva@gmail.com",
        role: "parent",
        avatarUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuD7E4wQ6ikYUBfwnfT7fG6yICfwaP_MY7y1qmuJBssWDkxnsLliMIZwZ2G8WB3RLuIT8T1KKJg_cDshSa8sDkiZvTIJ25LExQzxiyy_ouxDtNONNakSiewoLikfNQnnPPgRsWXtCG1I05uiMnaEdRlvS8Z0biwcBFMxwvlBOwe2VNNeR8wzzZ29iGuxihuMqCZN9uHQ-zx-75Ja3-pxy7ZF4dBb107nvujxturBP0CAs95_Y39gwWhLD3otz4GxtqNi9mKiLnszV7KV"
      };
    } else if (role === "guardian") {
      userDetails = {
        id: "user_guardian_01",
        name: "Trần Thị B",
        email: "nanny.ttb@gmail.com",
        role: "guardian",
        avatarUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuBCI0FXHpLQfLFj-6UNQcNILtpX4Ajx_iVZ6ArMjZMDlobInLvawDiinSEI1I4aGrVGi411KmsEIXi_HFWgdRRFXimVDuO1VFNikXE0rAYlLvQVvqxFC8kxXeNJYUDyF7q_FCNC8ksbh__0ZzS1sjElTAOMfQcSfTOam24TsQebg6WDKnObDWlL-VSEU69WzQ7U9xhmZYDIWTOd6aYZXOoqVwKbBd2YlDUXwNDK0ypE2CEM5OBRbxCmp728suzlZ_obf1nTO9IDfxjP"
      };
    } else {
      userDetails = {
        id: "user_viewer_01",
        name: "Viewer Guest",
        email: "guest@example.com",
        role: "viewer"
      };
    }

    const dummyToken = `dummy-jwt-token-for-${role}-${Date.now()}`;
    setToken(dummyToken);
    setUser(userDetails);
    localStorage.setItem("safekid_token", dummyToken);
    localStorage.setItem("safekid_user", JSON.stringify(userDetails));
    return true;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("safekid_token");
    localStorage.removeItem("safekid_user");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        logout,
        isAuthenticated: !!token
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
