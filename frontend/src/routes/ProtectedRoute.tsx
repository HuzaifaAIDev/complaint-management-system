import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Role } from "../types";

interface Props {
  children: React.ReactNode;
  roles?: Role[];
}

/**
 * This is a UX convenience only. Every backend endpoint independently
 * enforces role-based and object-level authorization - a user cannot
 * gain access to anything by bypassing this component.
 */
export default function ProtectedRoute({ children, roles }: Props) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="page-loading">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (user.must_change_password && location.pathname !== "/change-password-required") {
    return <Navigate to="/change-password-required" replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
