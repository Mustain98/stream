import { Suspense } from "react";

import { AuthForm } from "../../components/auth-form";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="center-card">Loading login...</div>}>
      <AuthForm mode="login" />
    </Suspense>
  );
}
