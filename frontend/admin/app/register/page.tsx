"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Button, Card, ErrorText, Field, Input } from "@/components/ui";

export default function RegisterPage() {
  const { register } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(username, email, password);
      // Full reload (not router.push) so the dashboard always starts from a
      // clean, freshly-fetched state right after auth.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/restaurant";
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ro'yxatdan o'tishda xatolik yuz berdi.");
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 font-[family-name:var(--font-display)] text-xl italic text-[var(--ink)]">Restoran egasi bo&apos;lib qo&apos;shiling</h1>
        <p className="mb-5 text-sm text-[var(--ink-muted)]">Ro&apos;yxatdan o&apos;tgach, o&apos;z restoraningizni yaratasiz.</p>
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <Field label="Login">
            <Input value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
          </Field>
          <Field label="Email">
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field label="Parol">
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
          </Field>
          <ErrorText>{error}</ErrorText>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Yuborilmoqda..." : "Ro'yxatdan o'tish"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-[var(--ink-muted)]">
          Hisobingiz bormi?{" "}
          <Link href="/login" className="font-medium text-[var(--ink)] underline">
            Kirish
          </Link>
        </p>
      </Card>
    </main>
  );
}
