import { oidcSpa } from "oidc-spa/react-spa";

export type DecodedIdToken = {
  sub: string;
  email?: string;
  preferred_username?: string;
  name?: string;
};

const issuerUri = import.meta.env.VITE_KEYCLOAK_ISSUER_URL ?? "http://localhost:8080/realms/taste-kid";
const clientId = import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? "taste-kid-web";

export const oidc = oidcSpa
  .withExpectedDecodedIdTokenShape<DecodedIdToken>({
    decodedIdTokenSchema: {
      parse: (input) => input as unknown as DecodedIdToken,
    },
  })
  .createUtils();

export function bootstrapOidc(): void {
  void oidc.bootstrapOidc({
    implementation: "real",
    issuerUri,
    clientId,
    scopes: ["profile", "email", "offline_access"],
    BASE_URL: window.location.origin,
  });
}

export async function ensureLoggedIn(): Promise<void> {
  const state = await oidc.getOidc();
  if (state.isUserLoggedIn) {
    return;
  }
  await state.login({});
}

export async function getAccessToken(): Promise<string | null> {
  const state = await oidc.getOidc();
  if (!state.isUserLoggedIn) {
    return null;
  }
  return await state.getAccessToken();
}

export async function logout(): Promise<void> {
  const state = await oidc.getOidc();
  if (!state.isUserLoggedIn) {
    return;
  }
  await state.logout({ redirectTo: "home" });
}
