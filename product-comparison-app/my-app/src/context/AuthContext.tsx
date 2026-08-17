"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { UserProfile, UserPreferences } from "../app/types";
import {
  loginUser as apiLogin,
  registerUser as apiRegister,
  googleAuthLogin as apiGoogleLogin,
  getProfile as apiGetProfile,
  updateProfile as apiUpdateProfile,
  uploadProfileImage as apiUploadProfileImage,
  removeProfileImage as apiRemoveProfileImage,
  updatePreferences as apiUpdatePreferences,
  changeAccountPassword as apiChangePassword,
} from "../services/api";

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  role: string;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string, confirmPassword?: string) => Promise<void>;
  googleLogin: (credential: string) => Promise<void>;
  logout: () => void;
  setPassword: (newPassword: string, confirmPassword?: string) => Promise<void>;
  updateUserProfile: (data: Partial<UserProfile> & { currentPassword?: string; newPassword?: string }) => Promise<UserProfile>;
  uploadProfileImage: (file: File) => Promise<UserProfile>;
  removeProfileImage: () => Promise<UserProfile>;
  updateUserPreferences: (data: Partial<UserPreferences>) => Promise<UserPreferences>;
  changePassword: (data: { currentPassword: string; newPassword: string }) => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string>("user");
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize auth state from localStorage and fetch live profile
  useEffect(() => {
    const initAuth = async () => {
      try {
        const savedToken = localStorage.getItem("versus_ai_jwt");
        if (savedToken) {
          setToken(savedToken);
          try {
            const profile = await apiGetProfile();
            setUser(profile);
            setRole(profile.role || (profile.isAdmin ? "admin" : "user"));
          } catch {
            // Token may have expired
            localStorage.removeItem("versus_ai_jwt");
            setToken(null);
            setUser(null);
          }
        }
      } catch (err) {
        console.error("Error initializing auth:", err);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const data = await apiLogin(email, password);
      setToken(data.token);
      setRole(data.role || "user");
      const profile = await apiGetProfile();
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (name: string, email: string, password: string, confirmPassword?: string) => {
    setIsLoading(true);
    try {
      const data = await apiRegister(name, email, password, confirmPassword);
      setToken(data.token);
      setRole(data.role || "user");
      const profile = await apiGetProfile();
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  };

  const googleLogin = async (credential: string) => {
    setIsLoading(true);
    try {
      const data = await apiGoogleLogin(credential);
      setToken(data.token);
      setRole(data.role || "user");
      const profile = await apiGetProfile();
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("versus_ai_jwt");
    setToken(null);
    setUser(null);
    setRole("user");
  };

  const setPassword = async (newPassword: string, confirmPassword?: string) => {
    await apiUpdateProfile({ newPassword });
    const profile = await apiGetProfile();
    setUser(profile);
  };

  const updateUserProfile = async (data: Partial<UserProfile> & { currentPassword?: string; newPassword?: string }): Promise<UserProfile> => {
    const updated = await apiUpdateProfile(data);
    setUser(updated);
    return updated;
  };

  const uploadProfileImage = async (file: File): Promise<UserProfile> => {
    const updated = await apiUploadProfileImage(file);
    setUser(updated);
    return updated;
  };

  const removeProfileImage = async (): Promise<UserProfile> => {
    const updated = await apiRemoveProfileImage();
    setUser(updated);
    return updated;
  };

  const updateUserPreferences = async (data: Partial<UserPreferences>): Promise<UserPreferences> => {
    const updated = await apiUpdatePreferences(data);
    if (user) {
      setUser({
        ...user,
        preferences: updated,
      });
    }
    return updated;
  };

  const changePassword = async (data: { currentPassword: string; newPassword: string }) => {
    await apiChangePassword(data);
  };

  const refreshUser = async () => {
    if (token) {
      try {
        const profile = await apiGetProfile();
        setUser(profile);
      } catch (err) {
        console.error("Failed to refresh user:", err);
      }
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        register,
        googleLogin,
        logout,
        setPassword,
        updateUserProfile,
        uploadProfileImage,
        removeProfileImage,
        updateUserPreferences,
        changePassword,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
