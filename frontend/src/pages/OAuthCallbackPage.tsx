import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LoadingState } from "../components/Common";
import { getHomePath } from "../utils/roleHome";

export default function OAuthCallbackPage() {
  const { refresh, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (user) {
      navigate(user.must_change_password ? "/change-password-required" : getHomePath(user.role), { replace: true });
    }
  }, [user, navigate]);

  return (
    <div className="auth-page">
      <div className="auth-form-side" style={{ gridColumn: "1 / -1" }}>
        <LoadingState label="Finishing sign-in..." />
      </div>
    </div>
  );
}
