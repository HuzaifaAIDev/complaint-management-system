import React from "react";
import { Link } from "react-router-dom";
import { Compass, Radar } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { getHomePath } from "../utils/roleHome";

export default function NotFoundPage() {
  const { user } = useAuth();
  return (
    <div className="notfound-page">
      <div className="notfound-card">
        <span className="sidebar-brand-mark notfound-mark"><Radar size={20} color="#fff" /></span>
        <span className="notfound-code">404</span>
        <h1>This page took a wrong turn.</h1>
        <p>The page you're looking for doesn't exist, or may have moved.</p>
        <Link className="btn-primary btn-lg" to={user ? getHomePath(user.role) : "/"}>
          <Compass size={16} /> {user ? "Back home" : "Back to home"}
        </Link>
      </div>
    </div>
  );
}
