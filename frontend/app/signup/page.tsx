import { Suspense } from "react";

import { AuthForm } from "../../components/auth-form";

export default function SignupPage() {
  return (
    <Suspense fallback={<div className="center-card">Loading signup...</div>}>
      <AuthForm mode="signup" />
    </Suspense>
  );
}
