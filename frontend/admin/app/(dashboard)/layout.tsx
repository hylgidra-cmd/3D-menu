"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { RestaurantProvider } from "@/lib/restaurant";
import Sidebar from "@/components/Sidebar";

function Guard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-[var(--ink-muted)]">Yuklanmoqda...</div>;
  }
  if (!user) return null;

  return (
    <RestaurantProvider>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 p-8">{children}</div>
      </div>
    </RestaurantProvider>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <Guard>{children}</Guard>;
}
