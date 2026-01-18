import React from "react";
import ReactDOM from "react-dom/client";
import { oidcEarlyInit } from "oidc-spa";
import App from "./App";
import "./index.css";
import { bootstrapOidc, isOidcConfigured } from "./lib/oidc";

const { shouldLoadApp } = oidcEarlyInit({
  BASE_URL: window.location.origin,
});

if (shouldLoadApp) {
  if (isOidcConfigured()) {
    bootstrapOidc();
  }

  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}
