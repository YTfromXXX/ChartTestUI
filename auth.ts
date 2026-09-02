import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

export const { handlers, auth, signIn, signOut } = NextAuth({
  session: { strategy: "jwt" },
  providers: [
    Credentials({
      id: "observer-credentials",
      name: "Observer credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        const email = String(credentials?.email ?? "").trim().toLowerCase();
        const password = String(credentials?.password ?? "");
        if (!email || !password) return null;
        const response = await fetch(`${process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/token`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ username: email, password }),
          cache: "no-store",
        }).catch(() => null);
        return response?.ok ? { id: email, email, name: "Observer" } : null;
      },
    }),
    Credentials({
      id: "siwe",
      name: "Ethereum wallet (SIWE)",
      credentials: {
        message: { label: "SIWE message", type: "text" },
        signature: { label: "Wallet signature", type: "text" },
        address: { label: "Wallet address", type: "text" },
      },
      async authorize() {
        // SIWE verification belongs here once nonce storage and `siwe` are enabled.
        return null;
      },
    }),
  ],
});