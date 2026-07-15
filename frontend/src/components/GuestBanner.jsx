// GuestBanner.jsx
// Shows a banner at the top when user is in guest/demo mode
// Reminds them data will expire and offers conversion to permanent account

import { useEffect, useState } from "react";
import { useAuth } from "../context/useAuth";
import "./GuestBanner.css";

export default function GuestBanner() {
  const { user, logout } = useAuth();
  const [isGuest, setIsGuest] = useState(false);

  useEffect(() => {
    // Check if current user is a guest
    const guestFlag = sessionStorage.getItem("is_guest") === "true";
    setIsGuest(guestFlag && user !== null);
  }, [user]);

  if (!isGuest) return null;

  const handleConvert = () => {
    // Log out guest and let them sign up
    logout();
    // User will be redirected to auth page automatically
  };

  return (
    <div className="guest-banner">
      <div className="guest-banner-content">
        <span className="guest-banner-icon">🧪</span>
        <div className="guest-banner-text">
          <strong>Demo Mode</strong>
          <span className="guest-banner-separator">•</span>
          <span>Your workspace will be deleted in 24 hours</span>
        </div>
      </div>
      <button onClick={handleConvert} className="guest-banner-btn">
        Create Permanent Account
      </button>
    </div>
  );
}
