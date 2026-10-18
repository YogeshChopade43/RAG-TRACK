import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { api, ApiError, configureApi } from "@/lib/api";
import { notifySessionChanged } from "@/lib/sessionStore";
import type { Tokens, User } from "@/lib/types";

const REFRESH_INTERVAL_MS = 25 * 60 * 1000; // access tokens expire after 30 minutes
const SESSION_KEYS = ["llm_api_key", "llm_model", "llm_verified", "active_document"];

type AuthContextValue = {
  user: User | null;
  isAuthenticated: boolean;
  ready: boolean;
  login(email: string, password: string): Promise<void>;
  register(email: string, password: string, fullName?: string): Promise<void>;
  logout(): Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readUser(): User | null {
  try {
    return JSON.parse(localStorage.getItem("user") ?? "null");
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem("access_token"));
  const [user, setUser] = useState<User | null>(readUser);
  // Without a stored session there is nothing to verify
  const [ready, setReady] = useState(() => !localStorage.getItem("access_token"));

  // The API client reads tokens synchronously; saveTokens/clearSession keep this in sync
  const tokenRef = useRef(accessToken);

  const saveTokens = useCallback((t: Tokens) => {
    localStorage.setItem("access_token", t.access_token);
    localStorage.setItem("refresh_token", t.refresh_token);
    tokenRef.current = t.access_token;
    setAccessToken(t.access_token);
  }, []);

  const clearSession = useCallback(() => {
    ["access_token", "refresh_token", "user"].forEach((k) => localStorage.removeItem(k));
    SESSION_KEYS.forEach((k) => sessionStorage.removeItem(k));
    notifySessionChanged();
    tokenRef.current = null;
    setAccessToken(null);
    setUser(null);
  }, []);

  const loadUser = useCallback(async () => {
    const me = await api.me();
    localStorage.setItem("user", JSON.stringify(me));
    setUser(me);
  }, []);

  // Configure the client during the first render: child effects run before
  // this component's effects and may already call the API
  useState(() =>
    configureApi({
      getAccessToken: () => tokenRef.current,
      getRefreshToken: () => localStorage.getItem("refresh_token"),
      onTokens: saveTokens,
      onAuthFailure: clearSession,
      getLlm: () => ({
        key: sessionStorage.getItem("llm_api_key") ?? undefined,
        model: sessionStorage.getItem("llm_model") ?? undefined,
      }),
    })
  );

  // Verify a stored session once on load
  useEffect(() => {
    if (ready) return;
    loadUser()
      .catch((e) => {
        // 401 after a failed refresh already signed out via onAuthFailure;
        // anything else (server down) keeps the session and just reports it
        if (!(e instanceof ApiError && e.status === 401)) toast.error(e.message);
      })
      .finally(() => setReady(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isAuthenticated = !!accessToken;

  useEffect(() => {
    if (!isAuthenticated) return;
    const id = setInterval(() => void api.refresh(), REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [isAuthenticated]);

  const login = useCallback(
    async (email: string, password: string) => {
      saveTokens(await api.login(email, password));
      await loadUser().catch(() => {}); // the session is valid even if /me hiccups
    },
    [saveTokens, loadUser]
  );

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      await api.register(email, password, fullName);
      await login(email, password);
    },
    [login]
  );

  const logout = useCallback(async () => {
    await api.logout().catch(() => {}); // sign out locally even if the server is unreachable
    clearSession();
  }, [clearSession]);

  const value = useMemo(
    () => ({ user, isAuthenticated, ready, login, register, logout }),
    [user, isAuthenticated, ready, login, register, logout]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
