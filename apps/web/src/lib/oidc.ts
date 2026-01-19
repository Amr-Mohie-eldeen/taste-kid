import { oidcSpa } from "oidc-spa/react-spa";

export type DecodedIdToken = {
  sub: string;
  email?: string;
  preferred_username?: string;
  name?: string;
};

const issuerUri = import.meta.env.VITE_KEYCLOAK_ISSUER_URL;
const clientId = import.meta.env.VITE_KEYCLOAK_CLIENT_ID;

export function isOidcConfigured(): boolean {
  return Boolean(issuerUri && clientId);
}

export const oidc = oidcSpa
  .withExpectedDecodedIdTokenShape<DecodedIdToken>({
    decodedIdTokenSchema: {
      parse: (input) => input as unknown as DecodedIdToken,
    },
  })
  .createUtils();

export function bootstrapOidc(): void {
  if (!isOidcConfigured()) {
    return;
  }

  void oidc.bootstrapOidc({
    implementation: "real",
    issuerUri: issuerUri as string,
    clientId: clientId as string,
    scopes: ["profile", "email"],
    BASE_URL: window.location.origin,
  });
}

export async function ensureLoggedIn(params?: { action?: "login" | "register" }): Promise<void> {
  if (!isOidcConfigured()) {
    return;
  }

  const state = await oidc.getOidc();
  if (state.isUserLoggedIn) {
    return;
  }

  const kc_action = params?.action === "register" ? "REGISTER" : "LOGIN";

  await state.login({
    extraQueryParams: {
      kc_action,
    },
  });
}

export async function getAccessToken(): Promise<string | null> {
  if (!isOidcConfigured()) {
    return null;
  }

  const state = await oidc.getOidc();
  if (!state.isUserLoggedIn) {
    return null;
  }
  return await state.getAccessToken();
}

export async function logout(params?: { redirectTo?: "home" | "current page" }): Promise<void> {
  if (!isOidcConfigured()) {
    return;
  }

  const state = await oidc.getOidc();
  if (!state.isUserLoggedIn) {
    return;
  }
  await state.logout({ redirectTo: params?.redirectTo ?? "home" });
}
