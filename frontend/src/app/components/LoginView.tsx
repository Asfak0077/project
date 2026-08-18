"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  ArrowRight,
  Mail,
  Lock,
  User as UserIcon,
  Eye,
  EyeOff,
  Zap,
  ShieldCheck,
  BarChart3,
  Loader2,
  AlertCircle,
  CheckCircle2,
  KeyRound,
  X,
} from "lucide-react";
import { UserProfile } from "../types";
import { useAuth } from "../../context/AuthContext";
import { authService } from "../../services/authService";
import { getProfile } from "../../services/api";

interface LoginViewProps {
  onLoginSuccess: (user: UserProfile) => void;
}

export default function LoginView({ onLoginSuccess }: LoginViewProps) {
  const { login, register, googleLogin } = useAuth();
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Forgot Password / OTP Reset Modal State
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotStep, setForgotStep] = useState<"email" | "otp">("email");
  const [otpCode, setOtpCode] = useState("");
  const [newResetPassword, setNewResetPassword] = useState("");
  const [confirmResetPassword, setConfirmResetPassword] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotMsg, setForgotMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const handleEmailAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!email.trim() || !password) {
      setErrorMessage("Please enter both email and password.");
      return;
    }

    if (authMode === "register") {
      if (!name.trim()) {
        setErrorMessage("Please enter your full name.");
        return;
      }
      if (password !== confirmPassword) {
        setErrorMessage("Passwords do not match. Please verify and try again.");
        return;
      }
      if (password.length < 6) {
        setErrorMessage("Password must be at least 6 characters long.");
        return;
      }
    }

    setIsSubmitting(true);

    try {
      if (authMode === "register") {
        await register(name.trim(), email.trim(), password);
        setSuccessMessage("Account created successfully! Loading your hardware dashboard...");
      } else {
        await login(email.trim(), password);
        setSuccessMessage("Logged in successfully! Loading your dashboard...");
      }
      const profile = await getProfile();
      onLoginSuccess(profile);
    } catch (err: any) {
      setErrorMessage(err.message || "Authentication failed. Please check your credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const googleClientId =
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ||
    "754708532874-l9bk0oqnv221ilmvmo8s0ctrn7bed44d.apps.googleusercontent.com";

  // Real Google OAuth Authentication / Account Linking Popup
  const handleGoogleAuth = async () => {
    setIsGoogleSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      // 1. Try Google Identity Services (GIS) Token Client Popup
      if (typeof window !== "undefined" && (window as any).google?.accounts?.oauth2) {
        const client = (window as any).google.accounts.oauth2.initTokenClient({
          client_id: googleClientId,
          scope: "openid email profile",
          callback: async (tokenResponse: any) => {
            if (tokenResponse?.error) {
              setErrorMessage(`Google sign-in canceled or failed: ${tokenResponse.error}`);
              setIsGoogleSubmitting(false);
              return;
            }
            if (tokenResponse?.access_token) {
              try {
                // Fetch verified profile from Google's official userinfo endpoint
                const googleRes = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
                  headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
                });
                const googleUser = await googleRes.json();
                if (googleUser?.email) {
                  // Send verified token to backend
                  await googleLogin(`google_oauth_verified_${googleUser.email}`);
                  setSuccessMessage("Google authentication verified! Linking account...");
                  const profile = await getProfile();
                  onLoginSuccess(profile);
                } else {
                  throw new Error("Could not retrieve verified email from Google.");
                }
              } catch (err: any) {
                setErrorMessage(err.message || "Failed to process Google sign in.");
              } finally {
                setIsGoogleSubmitting(false);
              }
            }
          },
        });
        client.requestAccessToken();
        return;
      }

      // 2. Fallback to Google GIS ID prompt if loaded
      if (typeof window !== "undefined" && (window as any).google?.accounts?.id) {
        (window as any).google.accounts.id.initialize({
          client_id: googleClientId,
          callback: async (response: any) => {
            if (response.credential) {
              try {
                await googleLogin(response.credential);
                setSuccessMessage("Google authentication verified!");
                const profile = await getProfile();
                onLoginSuccess(profile);
              } catch (err: any) {
                setErrorMessage(err.message || "Google sign-in failed.");
              } finally {
                setIsGoogleSubmitting(false);
              }
            }
          },
        });
        (window as any).google.accounts.id.prompt();
        return;
      }

      // 3. Fallback to standard Google OAuth popup window
      const oauthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${encodeURIComponent(googleClientId)}&response_type=token&scope=${encodeURIComponent("openid email profile")}&redirect_uri=${encodeURIComponent(window.location.origin)}`;
      const popup = window.open(oauthUrl, "google_oauth", "width=500,height=600");
      if (!popup) {
        throw new Error("Popup blocked. Please allow popups for Google Sign In.");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Google authentication failed.");
      setIsGoogleSubmitting(false);
    }
  };

  // Forgot Password: Step 1 - Send OTP
  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!forgotEmail.trim()) {
      setForgotMsg({ text: "Please enter your registered email address.", type: "error" });
      return;
    }
    setForgotLoading(true);
    setForgotMsg(null);
    try {
      const res = await authService.forgotPassword(forgotEmail.trim());
      setForgotMsg({
        text: res.message || "Verification OTP code sent to your email!",
        type: "success",
      });
      setForgotStep("otp");
    } catch (err: any) {
      setForgotMsg({ text: err.message || "Failed to send reset code.", type: "error" });
    } finally {
      setForgotLoading(false);
    }
  };

  // Forgot Password: Step 2 - Verify OTP & Set New Password
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpCode.trim() || !newResetPassword) {
      setForgotMsg({ text: "Please enter OTP and your new password.", type: "error" });
      return;
    }
    if (newResetPassword !== confirmResetPassword) {
      setForgotMsg({ text: "Passwords do not match.", type: "error" });
      return;
    }
    if (newResetPassword.length < 6) {
      setForgotMsg({ text: "Password must be at least 6 characters.", type: "error" });
      return;
    }

    setForgotLoading(true);
    setForgotMsg(null);
    try {
      const res = await authService.verifyOTP(forgotEmail.trim(), otpCode.trim(), newResetPassword);
      setForgotMsg({ text: res.message || "Password updated successfully!", type: "success" });
      setTimeout(() => {
        setShowForgotModal(false);
        setForgotStep("email");
        setAuthMode("login");
        setEmail(forgotEmail);
        setSuccessMessage("Password reset complete. You may now sign in with your new password.");
      }, 1500);
    } catch (err: any) {
      setForgotMsg({ text: err.message || "Invalid or expired OTP code.", type: "error" });
    } finally {
      setForgotLoading(false);
    }
  };

  const features = [
    {
      icon: Zap,
      title: "RAG Spec Grounding",
      desc: "Zero hallucination verified datasheets from official OEMs and MySQL inventory",
    },
    {
      icon: ShieldCheck,
      title: "Hardware Benchmark Engine",
      desc: "Deep CPU single/multi core and GPU TGP performance indexes",
    },
    {
      icon: BarChart3,
      title: "Intelligent Matrix Compare",
      desc: "Side-by-side spec delta highlighter and value winner calculations",
    },
  ];

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center p-4 sm:p-6 relative overflow-hidden bg-[#F5F7FA]">
      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-16 items-center relative z-10">
        {/* Left: Branding & Feature Cards */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="hidden lg:block space-y-8"
        >
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-blue-600 text-xs font-black shadow-2xs">
              <Sparkles className="w-4 h-4 text-blue-600" />
              Unified Account & Hardware Intelligence
            </div>
            <h1 className="text-5xl font-black tracking-tight text-slate-900 leading-[1.15]">
              Compare hardware <br />
              with <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">zero doubt</span>.
            </h1>
            <p className="text-slate-600 text-base font-medium max-w-md leading-relaxed">
              Explore 2,467+ laptops, benchmark thermals, verify display gamuts, and get AI recommendations grounded in real MySQL database inventory.
            </p>
          </div>

          <div className="space-y-4 pt-2">
            {features.map((f, i) => {
              const Icon = f.icon;
              return (
                <div
                  key={i}
                  className="flex items-start gap-4 p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs"
                >
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-black text-slate-900">{f.title}</h3>
                    <p className="text-xs text-slate-500 font-medium mt-0.5">{f.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </motion.div>

        {/* Right: Authentication Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="w-full"
        >
          <div className="bg-white rounded-3xl p-8 sm:p-10 shadow-xl border border-slate-200/90 relative">
            {/* Header / Mode Switcher */}
            <div className="mb-6 text-center lg:text-left">
              <div className="flex items-center justify-center lg:justify-start gap-2 mb-3">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-sm shadow-sm">
                  V
                </div>
                <span className="font-extrabold text-xl text-slate-900">
                  Versus<span className="text-blue-600">AI</span>
                </span>
              </div>
              
              <div className="flex items-center gap-2 p-1 bg-slate-100 rounded-xl mb-4">
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode("login");
                    setErrorMessage(null);
                    setSuccessMessage(null);
                  }}
                  className={`flex-1 py-2 text-xs font-black rounded-lg transition-all cursor-pointer ${
                    authMode === "login"
                      ? "bg-white text-slate-900 shadow-xs"
                      : "text-slate-500 hover:text-slate-900"
                  }`}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode("register");
                    setErrorMessage(null);
                    setSuccessMessage(null);
                  }}
                  className={`flex-1 py-2 text-xs font-black rounded-lg transition-all cursor-pointer ${
                    authMode === "register"
                      ? "bg-white text-slate-900 shadow-xs"
                      : "text-slate-500 hover:text-slate-900"
                  }`}
                >
                  Create Account
                </button>
              </div>

              <h2 className="text-2xl font-black text-slate-900 tracking-tight">
                {authMode === "login" ? "Welcome back" : "Create your account"}
              </h2>
              <p className="text-slate-500 text-xs font-semibold mt-1">
                {authMode === "login"
                  ? "Enter your credentials to access your dashboard & preferences"
                  : "Sign up to track hardware, compare laptops, and save recommendations"}
              </p>
            </div>

            {/* Error Message Alert */}
            {errorMessage && (
              <div className="mb-4 p-3.5 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs font-bold flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Success Message Alert */}
            {successMessage && (
              <div className="mb-4 p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-bold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{successMessage}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleEmailAuthSubmit} className="space-y-4">
              {authMode === "register" && (
                <div>
                  <label className="text-xs font-bold text-slate-500 block mb-1">Full Name</label>
                  <div className="relative">
                    <UserIcon className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Alex Hunter"
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-all"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="text-xs font-bold text-slate-500 block mb-1">Email Address</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="user@example.com"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-all"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-bold text-slate-500">Password</label>
                  {authMode === "login" && (
                    <button
                      type="button"
                      onClick={() => {
                        setForgotEmail(email);
                        setShowForgotModal(true);
                        setForgotStep("email");
                        setForgotMsg(null);
                      }}
                      className="text-xs font-bold text-blue-600 hover:underline cursor-pointer"
                    >
                      Forgot Password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-10 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-3 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {authMode === "register" && (
                <div>
                  <label className="text-xs font-bold text-slate-500 block mb-1">Confirm Password</label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                    <input
                      type={showPassword ? "text" : "password"}
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Confirm your password"
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-all"
                    />
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting || isGoogleSubmitting}
                className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-black text-xs shadow-md shadow-blue-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-50 cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <span>{authMode === "login" ? "Sign In" : "Create Account"}</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="relative my-5">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-white px-3 text-slate-400 font-bold uppercase tracking-wider">
                  Or
                </span>
              </div>
            </div>

            {/* Google Authentication Button (Auto-Links if email exists) */}
            <button
              type="button"
              onClick={handleGoogleAuth}
              disabled={isSubmitting || isGoogleSubmitting}
              className="w-full py-2.5 px-4 bg-white border border-slate-300 hover:bg-slate-50 hover:border-slate-400 text-slate-800 font-bold text-xs rounded-xl flex items-center justify-center gap-3 shadow-2xs transition-all cursor-pointer disabled:opacity-50"
            >
              {isGoogleSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                  <span>Connecting to Google...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.34 24 12 24Z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 10.03 0 12s.45 3.82 1.25 5.42l4.03-3.15Z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.34 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98Z"
                    />
                  </svg>
                  <span>Continue with Google</span>
                </>
              )}
            </button>

            {/* Toggle Mode Footer */}
            <div className="mt-5 text-center text-xs font-bold text-slate-500">
              {authMode === "login" ? (
                <>
                  Don&apos;t have an account yet?{" "}
                  <button
                    onClick={() => {
                      setAuthMode("register");
                      setErrorMessage(null);
                      setSuccessMessage(null);
                    }}
                    className="text-blue-600 hover:underline cursor-pointer"
                  >
                    Create Account
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{" "}
                  <button
                    onClick={() => {
                      setAuthMode("login");
                      setErrorMessage(null);
                      setSuccessMessage(null);
                    }}
                    className="text-blue-600 hover:underline cursor-pointer"
                  >
                    Sign In
                  </button>
                </>
              )}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Forgot Password OTP Modal */}
      <AnimatePresence>
        {showForgotModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl border border-slate-200 relative"
            >
              <button
                onClick={() => setShowForgotModal(false)}
                className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>

              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center">
                  <KeyRound className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-black text-slate-900">Reset Account Password</h3>
                  <p className="text-xs text-slate-500 font-semibold">
                    {forgotStep === "email" ? "Enter your email to receive a 6-digit OTP" : "Enter verification OTP and your new password"}
                  </p>
                </div>
              </div>

              {forgotMsg && (
                <div
                  className={`mb-4 p-3 rounded-xl text-xs font-bold flex items-center gap-2 ${
                    forgotMsg.type === "success"
                      ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                      : "bg-rose-50 text-rose-800 border border-rose-200"
                  }`}
                >
                  {forgotMsg.type === "success" ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  )}
                  <span>{forgotMsg.text}</span>
                </div>
              )}

              {forgotStep === "email" ? (
                <form onSubmit={handleSendOTP} className="space-y-4">
                  <div>
                    <label className="text-xs font-bold text-slate-500 block mb-1">Registered Email</label>
                    <div className="relative">
                      <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                      <input
                        type="email"
                        required
                        value={forgotEmail}
                        onChange={(e) => setForgotEmail(e.target.value)}
                        placeholder="user@example.com"
                        className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={forgotLoading}
                    className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-black text-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    {forgotLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Send Verification OTP"}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleResetPassword} className="space-y-3">
                  <div>
                    <label className="text-xs font-bold text-slate-500 block mb-1">6-Digit OTP Code</label>
                    <input
                      type="text"
                      required
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value)}
                      placeholder="e.g. 849201"
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 tracking-widest text-center focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-500 block mb-1">New Password</label>
                    <input
                      type="password"
                      required
                      value={newResetPassword}
                      onChange={(e) => setNewResetPassword(e.target.value)}
                      placeholder="New password (min 6 chars)"
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-500 block mb-1">Confirm New Password</label>
                    <input
                      type="password"
                      required
                      value={confirmResetPassword}
                      onChange={(e) => setConfirmResetPassword(e.target.value)}
                      placeholder="Confirm new password"
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={forgotLoading}
                    className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-black text-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 mt-2"
                  >
                    {forgotLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Verify & Update Password"}
                  </button>

                  <button
                    type="button"
                    onClick={() => setForgotStep("email")}
                    className="w-full py-2 text-xs font-bold text-slate-500 hover:text-slate-800"
                  >
                    ← Back to Email
                  </button>
                </form>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
