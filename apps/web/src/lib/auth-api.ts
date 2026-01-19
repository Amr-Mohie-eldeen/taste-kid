
const ISSUER = import.meta.env.VITE_KEYCLOAK_ISSUER_URL;
const CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID;

if (!ISSUER || !CLIENT_ID) {
  console.error("Missing Keycloak env vars");
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  id_token: string;
  token_type: string;
  not_before_policy: number;
  session_state: string;
  scope: string;
}

export const authApi = {
  async login(email: string, password: string): Promise<AuthResponse> {
    const params = new URLSearchParams();
    params.append("grant_type", "password");
    params.append("client_id", CLIENT_ID);
    params.append("username", email);
    params.append("password", password);
    params.append("scope", "openid profile email");

    const response = await fetch(`${ISSUER}/protocol/openid-connect/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error_description || "Failed to login");
    }

    return response.json();
  },

  async refreshToken(refreshToken: string): Promise<AuthResponse> {
    const params = new URLSearchParams();
    params.append("grant_type", "refresh_token");
    params.append("client_id", CLIENT_ID);
    params.append("refresh_token", refreshToken);

    const response = await fetch(`${ISSUER}/protocol/openid-connect/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params,
    });

    if (!response.ok) {
      throw new Error("Failed to refresh token");
    }

    return response.json();
  }
};
