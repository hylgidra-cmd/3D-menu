"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutGrid,
  Store,
  FolderTree,
  UtensilsCrossed,
  QrCode,
  Users,
  LogOut,
  type LucideIcon,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useRestaurant } from "@/lib/restaurant";
import { resolveMediaUrl } from "@/lib/api";

const links: { href: string; label: string; icon: LucideIcon; roles?: string[] }[] = [
  { href: "/", label: "Bosh sahifa", icon: LayoutGrid },
  { href: "/restaurant", label: "Restoran profili", icon: Store },
  { href: "/categories", label: "Kategoriyalar", icon: FolderTree },
  { href: "/menu", label: "Taomlar", icon: UtensilsCrossed },
  { href: "/tables", label: "Stollar / QR", icon: QrCode },
  { href: "/staff", label: "Xodimlar", icon: Users, roles: ["owner", "manager"] },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { restaurants, current, setCurrentId, loading } = useRestaurant();
  const logoUrl = resolveMediaUrl(current?.logo);

  return (
    <aside className="flex w-64 shrink-0 flex-col gap-6 border-r border-[var(--line)] bg-[var(--surface)] p-5">
      <div className="flex items-center gap-2.5 px-1">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[var(--ink)] font-[family-name:var(--font-display)] text-base italic text-white">
          M
        </span>
        <p className="font-[family-name:var(--font-display)] text-lg italic text-[var(--ink)]">Menu3D</p>
      </div>

      {!loading && current && (
        <div className="flex items-center gap-3 rounded-2xl bg-[var(--bg)] p-3">
          {logoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={logoUrl} alt="" className="h-9 w-9 shrink-0 rounded-lg object-cover" />
          ) : (
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[var(--surface)] ring-1 ring-[var(--line)]">
              <Store size={16} className="text-[var(--ink-muted)]" />
            </span>
          )}
          <div className="min-w-0 flex-1">
            {restaurants.length > 1 ? (
              <select
                value={current.id}
                onChange={(e) => setCurrentId(Number(e.target.value))}
                className="w-full truncate bg-transparent text-sm font-semibold text-[var(--ink)] outline-none"
              >
                {restaurants.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            ) : (
              <p className="truncate text-sm font-semibold text-[var(--ink)]">{current.name}</p>
            )}
            <p className="truncate text-xs text-[var(--ink-muted)]">{user?.username}</p>
          </div>
        </div>
      )}

      <nav className="flex flex-1 flex-col gap-0.5">
        {links
          .filter((link) => !link.roles || (current && link.roles.includes(current.role)))
          .map((link) => {
            const Icon = link.icon;
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-medium transition ${
                  active
                    ? "bg-[var(--ink)] text-white"
                    : "text-[var(--ink-muted)] hover:bg-[var(--bg)] hover:text-[var(--ink)]"
                }`}
              >
                <Icon size={17} strokeWidth={2} />
                {link.label}
              </Link>
            );
          })}
      </nav>

      <button
        onClick={logout}
        className="flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-medium text-[var(--ink-muted)] transition hover:bg-red-50 hover:text-red-600"
      >
        <LogOut size={17} strokeWidth={2} />
        Chiqish
      </button>
    </aside>
  );
}
