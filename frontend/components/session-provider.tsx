"use client";

import {
  createContext,
  ReactNode,
  startTransition,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

import { api, HttpError } from "../lib/api";
import type { User } from "../lib/types";

const STORAGE_KEY = "stream.auth.token";

type SessionContextValue = {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  signIn: (token: string) => Promise<User>;
  refreshUser: () => Promise<User | null>;
  signOut: () => void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const initialized = useRef(false);

  const signOut = () => {
    localStorage.removeItem(STORAGE_KEY);
    startTransition(() => {
      setToken(null);
      setUser(null);
      setIsLoading(false);
    });
  };

  const refreshUser = async () => {
    const activeToken = localStorage.getItem(STORAGE_KEY);
    if (!activeToken) {
      setToken(null);
      setUser(null);
      return null;
    }

    setToken(activeToken);
    try {
      const me = await api.me(activeToken);
      startTransition(() => {
        setUser(me);
      });
      return me;
    } catch (error) {
      if (error instanceof HttpError && error.status === 401) {
        signOut();
        return null;
      }
      throw error;
    }
  };

  const signIn = async (newToken: string) => {
    localStorage.setItem(STORAGE_KEY, newToken);
    setToken(newToken);
    const me = await api.me(newToken);
    startTransition(() => {
      setUser(me);
      setIsLoading(false);
    });
    return me;
  };

  useEffect(() => {
    if (initialized.current) {
      return;
    }

    initialized.current = true;

    const bootstrap = async () => {
      const storedToken = localStorage.getItem(STORAGE_KEY);
      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      try {
        await refreshUser();
      } catch (error) {
        console.error("Failed to restore session", error);
      } finally {
        setIsLoading(false);
      }
    };

    void bootstrap();
  }, []);

  return (
    <SessionContext.Provider
      value={{
        token,
        user,
        isLoading,
        signIn,
        refreshUser,
        signOut,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used inside SessionProvider");
  }
  return context;
}
