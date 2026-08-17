import axios from "axios";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const authApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach JWT token automatically
authApi.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("versus_ai_jwt");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor with unified error handling
authApi.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = "An error occurred during authentication.";
    if (error.response?.data?.detail) {
      message = typeof error.response.data.detail === "string"
        ? error.response.data.detail
        : JSON.stringify(error.response.data.detail);
    } else if (error.response?.status === 401) {
      message = "Session expired or invalid credentials.";
    } else if (error.request) {
      message = "Backend authentication server is unavailable (port 8000).";
    }
    return Promise.reject(new Error(message));
  }
);

export interface UserAuthData {
  id: number;
  name: string;
  email: string;
  role: string;
  avatar?: string;
  profile_image?: string;
  auth_provider: string;
}

export interface AuthResponse {
  token: string;
  access_token?: string;
  token_type: string;
  user_id: number;
  name: string;
  email: string;
  role: string;
  avatar?: string;
  user?: UserAuthData;
}

export const authService = {
  // Register with Email + Password
  register: async (name: string, email: string, password: string, confirmPassword?: string): Promise<AuthResponse> => {
    const res = await authApi.post<AuthResponse>("/auth/register", {
      name: name.trim(),
      email: email.toLowerCase().trim(),
      password,
      confirm_password: confirmPassword,
    });
    if (res.data?.token && typeof window !== "undefined") {
      localStorage.setItem("versus_ai_jwt", res.data.token);
    }
    return res.data;
  },

  // Login with Email + Password
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const res = await authApi.post<AuthResponse>("/auth/login", {
      email: email.toLowerCase().trim(),
      password,
    });
    if (res.data?.token && typeof window !== "undefined") {
      localStorage.setItem("versus_ai_jwt", res.data.token);
    }
    return res.data;
  },

  // Google Login / Link Existing Account
  googleLogin: async (credential: string): Promise<AuthResponse> => {
    const res = await authApi.post<AuthResponse>("/auth/google", {
      credential,
    });
    if (res.data?.token && typeof window !== "undefined") {
      localStorage.setItem("versus_ai_jwt", res.data.token);
    }
    return res.data;
  },

  // Get current user auth details
  getMe: async (): Promise<UserAuthData> => {
    const res = await authApi.get<UserAuthData>("/auth/me");
    return res.data;
  },

  // Logout
  logout: async (): Promise<void> => {
    try {
      await authApi.post("/auth/logout");
    } catch {
      // Ignore network errors on logout
    } finally {
      if (typeof window !== "undefined") {
        localStorage.removeItem("versus_ai_jwt");
      }
    }
  },

  // Set password for Google-created or existing accounts
  setPassword: async (newPassword: string, confirmPassword?: string): Promise<{ message: string; auth_provider: string }> => {
    const res = await authApi.post("/auth/set-password", {
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
    return res.data;
  },

  // Forgot password request OTP
  forgotPassword: async (email: string): Promise<{ message: string; otp_code?: string; otp_sent: boolean }> => {
    const res = await authApi.post("/auth/forgot-password", {
      email: email.toLowerCase().trim(),
    });
    return res.data;
  },

  // Verify OTP and reset password
  verifyOTP: async (email: string, otpCode: string, newPassword: string): Promise<{ message: string }> => {
    const res = await authApi.post("/auth/verify-otp", {
      email: email.toLowerCase().trim(),
      otp_code: otpCode.trim(),
      new_password: newPassword,
    });
    return res.data;
  },
};
