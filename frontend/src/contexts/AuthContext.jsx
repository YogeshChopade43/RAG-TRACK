import { createContext, useContext, useState, useEffect, useCallback } from "react";

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  const API_BASE = "http://127.0.0.1:8000";

  const loadTokensFromStorage = useCallback(() => {
    const storedAccess = localStorage.getItem("access_token");
    const storedRefresh = localStorage.getItem("refresh_token");
    const storedUser = localStorage.getItem("user");
    
    if (storedAccess && storedRefresh) {
      setAccessToken(storedAccess);
      setRefreshToken(storedRefresh);
      if (storedUser) {
        setUser(JSON.parse(storedUser));
      }
    }
    setIsInitialized(true);
  }, []);

  const refreshFromStorage = useCallback(() => {
    loadTokensFromStorage();
  }, [loadTokensFromStorage]);

  useEffect(() => {
    loadTokensFromStorage();
  }, [loadTokensFromStorage]);

  const saveTokens = useCallback((access, refresh) => {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
    setAccessToken(access);
    setRefreshToken(refresh);
  }, []);

  const clearTokens = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
  }, []);

  const fetchMe = useCallback(async (token) => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (res.ok) {
        const userData = await res.json();
        setUser(userData);
        localStorage.setItem("user", JSON.stringify(userData));
        return userData;
      }
    } catch (err) {
      console.error("Failed to fetch user:", err);
    }
    return null;
  }, []);

  const login = useCallback(async (email, password) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Login failed");
      }

      const data = await res.json();
      saveTokens(data.access_token, data.refresh_token);
      await fetchMe(data.access_token);
      
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    } finally {
      setIsLoading(false);
    }
  }, [saveTokens, fetchMe]);

  const register = useCallback(async (email, password, fullName) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password, full_name: fullName }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Registration failed");
      }

      const data = await res.json();
      return { success: true, data };
    } catch (err) {
      return { success: false, error: err.message };
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    if (accessToken) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });
      } catch (err) {
        console.error("Logout error:", err);
      }
    }
    clearTokens();
    sessionStorage.removeItem("llm_api_key");
  }, [accessToken, clearTokens]);

  const refreshTokenFn = useCallback(async () => {
    if (!refreshToken) return false;

    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) {
        clearTokens();
        return false;
      }

      const data = await res.json();
      saveTokens(data.access_token, data.refresh_token);
      return true;
    } catch (err) {
      clearTokens();
      return false;
    }
  }, [refreshToken, saveTokens, clearTokens]);

  const getAuthHeaders = useCallback(() => {
    return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
  }, [accessToken]);

  const value = {
    user,
    accessToken,
    isLoading,
    isInitialized,
    isAuthenticated: !!accessToken,
    login,
    register,
    logout,
    refreshTokenFn,
    getAuthHeaders,
    refreshFromStorage,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};