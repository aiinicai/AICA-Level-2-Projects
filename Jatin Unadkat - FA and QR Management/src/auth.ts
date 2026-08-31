import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import bcrypt from "bcryptjs";
import { prisma } from "@/lib/prisma";
import type { RoleName } from "@prisma/client";
import type { JWT } from "next-auth/jwt";

declare module "next-auth" {
  interface User {
    role?: RoleName;
  }
  interface Session {
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      role: RoleName;
    };
  }
}

// `declare module "next-auth/jwt"` augmentation doesn't resolve under this
// TS/bundler-resolution combo even though the plain import below does — so
// we extend the imported type locally instead of augmenting the module.
type AppJWT = JWT & { role?: RoleName; uid?: string };

export const { handlers, auth, signIn, signOut } = NextAuth({
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  // Required when self-hosting behind a reverse proxy/tunnel (Cloudflare
  // Tunnel, ngrok, etc.) whose forwarded Host header isn't known ahead of
  // time — without this, NextAuth rejects the request as an untrusted host.
  trustHost: true,
  providers: [
    Credentials({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      authorize: async (credentials) => {
        const email = credentials?.email as string | undefined;
        const password = credentials?.password as string | undefined;
        if (!email || !password) return null;

        const user = await prisma.user.findUnique({
          where: { email: email.toLowerCase() },
          include: { role: true },
        });
        if (!user || !user.isActive) return null;

        const valid = await bcrypt.compare(password, user.passwordHash);
        if (!valid) return null;

        await prisma.user.update({
          where: { id: user.id },
          data: { lastLoginAt: new Date() },
        });

        return {
          id: user.id,
          name: user.fullName,
          email: user.email,
          role: user.role.name,
        };
      },
    }),
  ],
  callbacks: {
    jwt: ({ token, user }) => {
      const t = token as AppJWT;
      if (user) {
        t.role = user.role;
        t.uid = user.id;
      }
      return t;
    },
    session: ({ session, token }) => {
      const t = token as AppJWT;
      if (session.user) {
        session.user.id = t.uid as string;
        session.user.role = t.role as RoleName;
      }
      return session;
    },
  },
});
