"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  FolderTree,
  UtensilsCrossed,
  QrCode,
  Users,
  Store,
  ArrowRight,
  type LucideIcon,
} from "lucide-react";
import { useRestaurant } from "@/lib/restaurant";
import { apiFetch, resolveMediaUrl } from "@/lib/api";
import { Card } from "@/components/ui";

type Counts = { categories: number | null; eats: number | null; tables: number | null };

const quickActions: { href: string; label: string; description: string; icon: LucideIcon }[] = [
  { href: "/categories", label: "Kategoriya qo'shish", description: "Menyuni bo'limlarga ajrating", icon: FolderTree },
  { href: "/menu", label: "Taom qo'shish", description: "Rasm bilan yangi taom yarating", icon: UtensilsCrossed },
  { href: "/tables", label: "Stol yaratish", description: "Har bir stol uchun QR kod oling", icon: QrCode },
  { href: "/staff", label: "Xodim taklif qilish", description: "Jamoangizga a'zo qo'shing", icon: Users },
];

export default function DashboardHome() {
  const { restaurants, current, loading } = useRestaurant();
  const router = useRouter();
  const [counts, setCounts] = useState<Counts>({ categories: null, eats: null, tables: null });

  useEffect(() => {
    if (!loading && restaurants.length === 0) router.replace("/restaurant");
  }, [loading, restaurants, router]);

  useEffect(() => {
    if (!current) return;
    let cancelled = false;
    (async () => {
      const [categories, eats, tables] = await Promise.all([
        apiFetch<{ count: number }>(`/api/eat/category/?restaurant=${current.id}`),
        apiFetch<{ count: number }>(`/api/eat/?restaurant=${current.id}`),
        apiFetch<{ count: number }>(`/api/table/?restaurant=${current.id}`),
      ]);
      if (!cancelled) {
        setCounts({ categories: categories.count, eats: eats.count, tables: tables.count });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [current]);

  if (loading) return <p className="text-sm text-[var(--ink-muted)]">Yuklanmoqda...</p>;
  if (!current) return null;

  const logoUrl = resolveMediaUrl(current.logo);
  const stats = [
    { label: "Kategoriyalar", value: counts.categories, href: "/categories" },
    { label: "Taomlar", value: counts.eats, href: "/menu" },
    { label: "Stollar", value: counts.tables, href: "/tables" },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4 rounded-2xl bg-[var(--surface)] p-5 ring-1 ring-[var(--line)]">
        {logoUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={logoUrl} alt="" className="h-14 w-14 shrink-0 rounded-xl object-cover" />
        ) : (
          <span className="grid h-14 w-14 shrink-0 place-items-center rounded-xl bg-[var(--bg)] ring-1 ring-[var(--line)]">
            <Store size={22} className="text-[var(--ink-muted)]" />
          </span>
        )}
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl font-bold text-[var(--ink)]">{current.name}</h1>
          <div className="mt-1 flex items-center gap-2 text-sm text-[var(--ink-muted)]">
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${current.is_active ? "bg-emerald-500" : "bg-red-500"}`}
            />
            {current.is_active ? "Faol" : "To'xtatilgan"}
            <span className="text-[var(--line)]">&middot;</span>
            <span className="capitalize">{current.role}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {stats.map((s) => (
          <Link key={s.label} href={s.href}>
            <Card className="transition hover:ring-[var(--ink)]/20">
              <p className="text-sm text-[var(--ink-muted)]">{s.label}</p>
              <p className="mt-1 text-2xl font-bold text-[var(--ink)]">{s.value ?? "-"}</p>
            </Card>
          </Link>
        ))}
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-[var(--ink-muted)]">Tezkor amallar</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {quickActions.map((a) => {
            const Icon = a.icon;
            return (
              <Link key={a.href} href={a.href}>
                <Card className="group flex items-center gap-3.5 transition hover:ring-[var(--ink)]/20">
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-[var(--bg)]">
                    <Icon size={19} className="text-[var(--ink)]" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-[var(--ink)]">{a.label}</p>
                    <p className="truncate text-sm text-[var(--ink-muted)]">{a.description}</p>
                  </div>
                  <ArrowRight
                    size={16}
                    className="shrink-0 text-[var(--ink-muted)] transition group-hover:translate-x-0.5 group-hover:text-[var(--ink)]"
                  />
                </Card>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
