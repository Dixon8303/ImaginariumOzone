import React, { createContext, useState, useContext, useEffect, useCallback } from "react";
import { cw } from "@/api/client";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const [isLoadingPublicSettings, setIsLoadingPublicSettings] = useState(true);
  const [authError, setAuthError] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [appPublicSettings, setAppPublicSettings] = useState(null);

  const checkUserAuth = useCallback(async () => {
    setIsLoadingAuth(true);
    try {
      if (!cw.getToken()) {
        setUser(null);
        setIsAuthenticated(false);
        return;
      }
      const me = await cw.auth.me();
      setUser(me);
      setIsAuthenticated(true);
    } catch (error) {
      if (error.status === 401) cw.auth.setToken(null);
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoadingAuth(false);
      setAuthChecked(true);
    }
  }, []);

  const checkAppState = useCallback(async () => {
    setIsLoadingPublicSettings(true);
    setAuthError(null);
    try {
      const settings = await cw.app.getPublicSettings();
      setAppPublicSettings(settings);
    } catch (error) {
      // The marketing site still renders; only server-backed features fail.
      setAuthError({ type: "server_unreachable", message: error.message || "Can't reach the CinemaWin server." });
    } finally {
      setIsLoadingPublicSettings(false);
    }
    await checkUserAuth();
  }, [checkUserAuth]);

  useEffect(() => {
    checkAppState();
  }, [checkAppState]);

  const logout = async (shouldRedirect = true) => {
    setUser(null);
    setIsAuthenticated(false);
    await cw.auth.logout(shouldRedirect ? "/" : undefined);
  };

  const navigateToLogin = () => {
    cw.auth.redirectToLogin(window.location.pathname + window.location.search);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoadingAuth,
        isLoadingPublicSettings,
        authError,
        appPublicSettings,
        authChecked,
        logout,
        navigateToLogin,
        checkUserAuth,
        checkAppState,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
};
