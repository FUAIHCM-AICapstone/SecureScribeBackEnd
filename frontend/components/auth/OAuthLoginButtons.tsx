"use client";
import React from "react";
import FirebaseAuth from "./FirebaseAuth";

interface OAuthLoginButtonsProps {
  onSuccess?: () => void;
}

const OAuthLoginButtons: React.FC<OAuthLoginButtonsProps> = ({
  onSuccess
}) => {
  const handleFirebaseSuccess = () => {
    // Handle successful Firebase authentication
    onSuccess?.();
  };

  return (
    <FirebaseAuth onSuccess={handleFirebaseSuccess} />
  );
};

export default OAuthLoginButtons;
