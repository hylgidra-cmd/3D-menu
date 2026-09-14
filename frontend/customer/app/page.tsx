export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 px-6 text-center">
      <h1 className="font-[family-name:var(--font-display)] text-2xl italic text-[var(--ink)]">
        Menu3D
      </h1>
      <p className="max-w-sm text-sm leading-relaxed text-[var(--ink-muted)]">
        Bu sahifa mustaqil ochilmaydi — restoran stolidagi QR kodni skanerlang,
        menyu va 3D/AR taomlar avtomatik ochiladi.
      </p>
    </main>
  );
}
