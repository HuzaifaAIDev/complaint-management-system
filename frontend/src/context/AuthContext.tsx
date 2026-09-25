import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { User } from "../types";
import * as authService from "../services/authService";
import { ApiError } from "../services/apiClient";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string, remember?: boolean) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const { user } = await authService.me();
      setUser(user);
      return user;
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setUser(null);
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = async (email: string, password: string, remember?: boolean) => {
    const { user } = await authService.login(email, password, remember);
    setUser(user);
    return user;
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
