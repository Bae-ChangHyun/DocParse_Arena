"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { getAuthStatus, adminLogin, setAdminToken } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Lock } from "lucide-react";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [checking, setChecking] = useState(true);
  const [authRequired, setAuthRequired] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loggingIn, setLoggingIn] = useState(false);

  useEffect(() => {
    getAuthStatus()
      .then(({ auth_required }) => {
        setAuthRequired(auth_required);
        if (!auth_required) setAuthenticated(true);
      })
      .catch((e) => toast.error("Failed to check auth status", { description: String(e) }))
      .finally(() => setChecking(false));
  }, []);

  const handleLogin = async () => {
    setLoggingIn(true);
    setLoginError("");
    try {
      const { token } = await adminLogin(password);
      setAdminToken(token);
      setAuthenticated(true);
    } catch {
      setLoginError("Invalid password");
    }
    setLoggingIn(false);
  };

  if (checking) {
    return (
      <div className="container mx-auto px-4 py-20 max-w-md text-center">
        <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
      </div>
    );
  }

  if (authRequired && !authenticated) {
    return (
      <div className="container mx-auto px-4 py-20 max-w-md">
        <Card>
          <CardHeader className="text-center">
            <div className="mx-auto mb-2 h-12 w-12 rounded-full bg-muted flex items-center justify-center">
              <Lock className="h-6 w-6 text-muted-foreground" />
            </div>
            <CardTitle>Admin Authentication</CardTitle>
            <CardDescription>Enter the admin password to access settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleLogin()}
                autoFocus
              />
              {loginError && (
                <p className="text-sm text-destructive">{loginError}</p>
              )}
            </div>
            <Button className="w-full" onClick={handleLogin} disabled={loggingIn || !password}>
              {loggingIn ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Sign In
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}
