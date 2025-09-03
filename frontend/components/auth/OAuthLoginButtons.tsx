"use client";
import { Button } from "antd";
import Cookies from "js-cookie";
import { useTranslations } from "next-intl";
import { useEffect } from "react";
import { FcGoogle } from "react-icons/fc";
import { openGoogleLoginPopup } from "services/api/auth";

const OAUTH_POPUP_MESSAGE_TYPES = ["GOOGLE_AUTH_SUCCESS", "AZURE_AUTH_SUCCESS"];

export default function OAuthLoginButtons() {
  const t = useTranslations("AuthLayout");

  useEffect(() => {
    function handleAuthMessage(event: MessageEvent) {
      // Optionally: check event.origin for security
      if (
        event.data &&
        typeof event.data === "object" &&
        OAUTH_POPUP_MESSAGE_TYPES.includes(event.data.type)
      ) {
        const { accessToken, refreshToken } = event.data;
        // Store tokens using js-cookie
        Cookies.set("access_token", accessToken, { sameSite: "Lax" });
        if (refreshToken) Cookies.set("refresh_token", refreshToken, { sameSite: "Lax" });
        // Optionally: trigger a reload or redirect
        window.location.reload();
      }
    }
    window.addEventListener("message", handleAuthMessage);
    return () => window.removeEventListener("message", handleAuthMessage);
  }, []);

  return (
    <>
      <Button
        type="primary"
        htmlType="button"
        icon={<FcGoogle size={24} />}
        onClick={openGoogleLoginPopup}
        size="large"
        block
        className="mb-2"
        style={{
          borderRadius: 12,
          background: "var(--primary-color)",
          border: "none",
          color: "#fff",
        }}
      >
        {t("loginGoogle")}
      </Button>
      {/* <Button
        type="primary"
        htmlType="button"
        icon={<FaMicrosoft size={22} />}
        onClick={openAzureLoginPopup}
        size="large"
        block
        className="mb-2"
        style={{
          borderRadius: 12,
          background: "var(--primary-color)",
          border: "none",
          color: "#fff",
        }}
      >
        {t("loginAzure")}
      </Button> */}
    </>
  );
}
