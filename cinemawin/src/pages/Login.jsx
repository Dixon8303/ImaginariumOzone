import React, { useState } from "react";
import { Link } from "react-router-dom";
import { cw, navigateHard } from "@/api/client";
import { useAuth } from "@/lib/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LogIn, Mail, Lock, Loader2 } from "lucide-react";
import AuthLayout from "@/components/AuthLayout";
import GoogleIcon from "@/components/GoogleIcon";
import { safeReturnTo } from "@/lib/authReturnTo";
import { postAuthDestination, hasPendingIntake } from "@/lib/intake";

export default function Login() {
  const { appPublicSettings } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [resent, setResent] = useState(false);
  const returnTo = safeReturnTo("/workspace");
  const googleEnabled = !!appPublicSettings?.google_oauth_enabled;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await cw.auth.loginViaEmailPassword(email, password);
      // Full navigation so the auth context re-initialises with the new token.
      navigateHard(await postAuthDestination(returnTo));
    } catch (err) {
      setError(err.message || "Invalid email or password");
      // An unverified account is otherwise a dead end: the code screen only
      // exists in the tab that registered. Offer a fresh code from here.
      setNeedsVerification(err.code === "email_not_verified");
      setLoading(false);
    }
  };

  const handleGoogle = () => {
    try {
      cw.auth.loginWithProvider("google", returnTo);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <AuthLayout
      icon={LogIn}
      title="Welcome back"
      subtitle={hasPendingIntake() ? "Sign in and we'll save the story you just developed." : "Log in to your account"}
      footer={
        <>
          Don't have an account?{" "}
          <Link to={"/register" + (returnTo !== "/workspace" ? "?returnTo=" + encodeURIComponent(returnTo) : "")} className="text-primary font-medium hover:underline">
            Create one
          </Link>
        </>
      }
    >
      {googleEnabled && (
        <>
          <Button variant="outline" className="w-full h-12 text-sm font-medium mb-6" onClick={handleGoogle}>
            <GoogleIcon className="w-5 h-5 mr-2" />
            Continue with Google
          </Button>
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-3 text-muted-foreground">or</span>
            </div>
          </div>
        </>
      )}

      {error && <div className="mb-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">{error}</div>}

      {needsVerification && (
        <div className="mb-4 rounded-lg border border-accent/40 bg-accent/10 p-3 text-sm">
          {resent ? (
            <span className="text-foreground">A new code is on its way. Check your email, then use the link below.</span>
          ) : (
            <>
              <span className="text-muted-foreground">Need a new verification code?</span>{" "}
              <button
                type="button"
                onClick={async () => {
                  try {
                    await cw.auth.resendOtp(email);
                  } catch {
                    /* never reveal whether the address exists */
                  }
                  setResent(true);
                }}
                className="font-semibold text-accent hover:underline"
              >
                Send one
              </button>
            </>
          )}
          {resent && (
            <Link to={`/register?returnTo=${encodeURIComponent(returnTo)}`} className="ml-1 font-semibold text-accent hover:underline">
              Enter it here
            </Link>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" aria-hidden="true" />
            <Input id="email" type="email" autoComplete="email" autoFocus placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} className="pl-10 h-12" required />
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link to="/forgot-password" className="text-xs text-primary hover:underline">
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" aria-hidden="true" />
            <Input id="password" type="password" autoComplete="current-password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} className="pl-10 h-12" required />
          </div>
        </div>
        <Button type="submit" className="w-full h-12 font-medium" disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Logging in...
            </>
          ) : (
            "Log in"
          )}
        </Button>
      </form>
    </AuthLayout>
  );
}
