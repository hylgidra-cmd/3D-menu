export default function MenuNotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-2 px-6 text-center">
      <h1 className="font-[family-name:var(--font-display)] text-xl text-[var(--ink)]">
        Menyu topilmadi
      </h1>
      <p className="max-w-xs text-sm leading-relaxed text-[var(--ink-muted)]">
        Bu QR kod yaroqsiz yoki stol faol emas. Iltimos, ofitsiantdan yordam so&apos;rang.
      </p>
    </main>
  );
}
