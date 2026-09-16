"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutGrid,
  Store,
  FolderTree,
  UtensilsCrossed,
  QrCode,
  ClipboardList,
  LogOut,
  Menu,
  X,
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
  { href: "/orders", label: "Buyurtmalar", icon: ClipboardList },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { restaurants, current, setCurrentId, loading } = useRestaurant();
  const logoUrl = resolveMediaUrl(current?.logo);
  const [mobileOpen, setMobileOpen] = useState(false);

  const visibleLinks = links.filter((link) => !link.roles || (current && link.roles.includes(current.role)));

  const brand = (
    <div className="flex items-center gap-2.5 px-1">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[var(--ink)] font-[family-name:var(--font-display)] text-base italic text-white">
        M
      </span>
      <p className="font-[family-name:var(--font-display)] text-lg italic text-[var(--ink)]">Menu3D</p>
    </div>
  );

  const restaurantSwitcher = !loading && current && (
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
  );

  const navLinks = (onNavigate?: () => void) => (
    <nav className="flex flex-1 flex-col gap-0.5">
      {visibleLinks.map((link) => {
        const Icon = link.icon;
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            onClick={onNavigate}
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
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col gap-6 border-r border-[var(--line)] bg-[var(--surface)] p-5 lg:flex">
        {brand}
        {restaurantSwitcher}
        {navLinks()}
        <button
          onClick={logout}
          className="flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-medium text-[var(--ink-muted)] transition hover:bg-red-50 hover:text-red-600"
        >
          <LogOut size={17} strokeWidth={2} />
          Chiqish
        </button>
      </aside>

      {/* Mobile top bar with menu button on the right */}
      <div className="flex items-center justify-between border-b border-[var(--line)] bg-[var(--surface)] px-4 py-3 lg:hidden">
        {brand}
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Menyu"
          className="flex h-9 w-9 items-center justify-center rounded-xl text-[var(--ink)] ring-1 ring-[var(--line)]"
        >
          <Menu size={18} strokeWidth={2} />
        </button>
      </div>

      {/* Mobile menu modal, drops down from the top bar */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" onClick={() => setMobileOpen(false)}>
          <div className="absolute inset-0 bg-black/30" />
          <div
            className="animate-menu-drop absolute inset-x-0 top-0 flex max-h-[85vh] flex-col gap-4 overflow-y-auto rounded-b-3xl bg-[var(--surface)] p-5 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              {brand}
              <button
                onClick={() => setMobileOpen(false)}
                aria-label="Yopish"
                className="flex h-9 w-9 items-center justify-center rounded-xl text-[var(--ink)] ring-1 ring-[var(--line)]"
              >
                <X size={18} strokeWidth={2} />
              </button>
            </div>
            {restaurantSwitcher}
            {navLinks(() => setMobileOpen(false))}
            <button
              onClick={() => {
                setMobileOpen(false);
                logout();
              }}
              className="flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-medium text-[var(--ink-muted)] transition hover:bg-red-50 hover:text-red-600"
            >
              <LogOut size={17} strokeWidth={2} />
              Chiqish
            </button>
          </div>
        </div>
      )}
    </>
  );
}
