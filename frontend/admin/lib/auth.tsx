"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { apiFetch, ApiError } from "./api";
import type { User } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://threed-menu-api.onrender.com";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const loadUserInFlight = useRef<Promise<void> | null>(null);

  const loadUser = () => {
    if (loadUserInFlight.current) return loadUserInFlight.current;

    const request = (async () => {
    // The access token lives in an httpOnly cookie, invisible to JS - the
    // only way to know if we're logged in is to just ask the API.
      try {
        const me = await apiFetch<User>("/api/user/me/", { redirectOnAuthFailure: false });
        setUser(me);
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    })();

    loadUserInFlight.current = request;
    request.finally(() => {
      if (loadUserInFlight.current === request) loadUserInFlight.current = null;
    });
    return request;
  };

  useEffect(() => {
    loadUser();
  }, []);

  const login = async (username: string, password: string) => {
    const res = await fetch(`${API_BASE_URL}/api/auth/login/`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      throw new ApiError(res.status, await res.json().catch(() => null));
    }
    await loadUser();
  };

  const register = async (username: string, email: string, password: string) => {
    await apiFetch("/api/user/", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
      auth: false,
    });
    await login(username, password);
  };

  const logout = async () => {
    await fetch(`${API_BASE_URL}/api/auth/logout/`, { method: "POST", credentials: "include" });
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
