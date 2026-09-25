import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import { ConfirmProvider } from "./context/ConfirmContext";
import { ThemeProvider } from "./context/ThemeContext";
import ProtectedRoute from "./routes/ProtectedRoute";
import AppLayout from "./layouts/AppLayout";

import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ChangePasswordRequiredPage from "./pages/ChangePasswordRequiredPage";
import OAuthCallbackPage from "./pages/OAuthCallbackPage";
import DashboardPage from "./pages/DashboardPage";
import RequestsListPage from "./pages/RequestsListPage";
import NewRequestPage from "./pages/NewRequestPage";
import RequestDetailPage from "./pages/RequestDetailPage";
import ComplaintsListPage from "./pages/ComplaintsListPage";
import NewComplaintPage from "./pages/NewComplaintPage";
import ComplaintDetailPage from "./pages/ComplaintDetailPage";
import SlaMonitoringPage from "./pages/SlaMonitoringPage";
import CustomerDetailPage from "./pages/CustomerDetailPage";
import AgentWorkloadPage from "./pages/AgentWorkloadPage";
import KanbanBoardPage from "./pages/KanbanBoardPage";
import AdminUsersPage from "./pages/AdminUsersPage";
import AdminCategoriesPage from "./pages/AdminCategoriesPage";
import AdminAuditLogsPage from "./pages/AdminAuditLogsPage";
import ProfilePage from "./pages/ProfilePage";
import CompleteProfilePage from "./pages/CompleteProfilePage";
import NotFoundPage from "./pages/NotFoundPage";
import { getHomePath } from "./utils/roleHome";

/**
 * The public homepage. Signed-out visitors land on the marketing page;
 * anyone already signed in is sent straight to their workspace instead of
 * seeing the pitch for a product they already use - customers go to their
 * simple request list, staff go to the analytics dashboard.
 */
function HomeRoute() {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loading">Loading...</div>;
  if (user) return <Navigate to={getHomePath(user.role)} replace />;
  return <LandingPage />;
}

/**
 * Gate for Google Sign-In customers who haven't supplied a phone number
 * and location yet (Google never provides either). Blocks the rest of
 * the app - not just certain pages - until the profile is complete, then
 * lets the customer through everywhere as normal.
 */
function ProfileGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loading">Loading...</div>;
  if (user && user.role === "customer" && user.profile_complete === false) {
    return <Navigate to="/complete-profile" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
      <ToastProvider>
        <ConfirmProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<HomeRoute />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/verify-email" element={<VerifyEmailPage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
              <Route path="/change-password-required" element={<ProtectedRoute><ChangePasswordRequiredPage /></ProtectedRoute>} />
              <Route path="/complete-profile" element={<ProtectedRoute roles={["customer"]}><CompleteProfilePage /></ProtectedRoute>} />

              <Route element={<ProtectedRoute><ProfileGate><AppLayout /></ProfileGate></ProtectedRoute>}>
                <Route path="/dashboard" element={<ProtectedRoute roles={["admin", "supervisor", "agent"]}><DashboardPage /></ProtectedRoute>} />

                <Route path="/requests" element={<RequestsListPage />} />
                <Route path="/requests/new" element={<ProtectedRoute roles={["customer"]}><NewRequestPage /></ProtectedRoute>} />
                <Route path="/requests/:id" element={<RequestDetailPage />} />

                <Route path="/complaints" element={<ComplaintsListPage />} />
                <Route path="/complaints/new" element={<ProtectedRoute roles={["customer"]}><NewComplaintPage /></ProtectedRoute>} />
                <Route path="/complaints/:id" element={<ComplaintDetailPage />} />

                <Route path="/sla-monitoring" element={<ProtectedRoute roles={["admin", "supervisor", "agent"]}><SlaMonitoringPage /></ProtectedRoute>} />
                <Route path="/customers/:id" element={<ProtectedRoute roles={["admin", "supervisor", "agent"]}><CustomerDetailPage /></ProtectedRoute>} />
                <Route path="/agents/workload" element={<ProtectedRoute roles={["admin", "supervisor"]}><AgentWorkloadPage /></ProtectedRoute>} />
                <Route path="/requests/board" element={<ProtectedRoute roles={["admin", "supervisor", "agent"]}><KanbanBoardPage /></ProtectedRoute>} />

                <Route path="/admin/users" element={<ProtectedRoute roles={["admin", "supervisor"]}><AdminUsersPage /></ProtectedRoute>} />
                <Route path="/admin/categories" element={<ProtectedRoute roles={["admin"]}><AdminCategoriesPage /></ProtectedRoute>} />
                <Route path="/admin/audit-logs" element={<ProtectedRoute roles={["admin", "supervisor"]}><AdminAuditLogsPage /></ProtectedRoute>} />
                <Route path="/profile" element={<ProfilePage />} />
              </Route>

              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </BrowserRouter>
        </ConfirmProvider>
      </ToastProvider>
      </ThemeProvider>
    </AuthProvider>
  );
}
