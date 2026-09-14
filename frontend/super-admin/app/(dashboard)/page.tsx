"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Button, Card } from "@/components/ui";
import type { PlatformStats, Restaurant } from "@/lib/types";

export default function SuperAdminDashboard() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [loading, setLoading] = useState(true);
  const [togglingId, setTogglingId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    const [statsData, restaurantsData] = await Promise.all([
      apiFetch<PlatformStats>("/api/restaurant/platform-stats/"),
      apiFetch<{ results: Restaurant[] }>("/api/restaurant/"),
    ]);
    setStats(statsData);
    setRestaurants(restaurantsData.results);
    setLoading(false);
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch dashboard data once on mount
    load();
  }, []);

  const toggleActive = async (restaurant: Restaurant) => {
    setTogglingId(restaurant.id);
    try {
      await apiFetch(`/api/restaurant/${restaurant.id}/activate/`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !restaurant.is_active }),
      });
      await load();
    } finally {
      setTogglingId(null);
    }
  };

  if (loading || !stats) return <p className="text-sm text-[var(--ink-muted)]">Yuklanmoqda...</p>;

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card>
          <p className="text-sm text-[var(--ink-muted)]">Restoranlar</p>
          <p className="text-2xl font-bold">{stats.restaurants.total}</p>
          <p className="text-xs text-[var(--ink-muted)]">{stats.restaurants.active} faol · {stats.restaurants.inactive} to&apos;xtatilgan</p>
        </Card>
        <Card>
          <p className="text-sm text-[var(--ink-muted)]">Foydalanuvchilar</p>
          <p className="text-2xl font-bold">{stats.users}</p>
        </Card>
        <Card>
          <p className="text-sm text-[var(--ink-muted)]">Stollar</p>
          <p className="text-2xl font-bold">{stats.tables}</p>
        </Card>
        <Card>
          <p className="text-sm text-[var(--ink-muted)]">Taomlar</p>
          <p className="text-2xl font-bold">{stats.eats.total}</p>
          <p className="text-xs text-[var(--ink-muted)]">{stats.eats.with_3d_model} ta 3D tayyor</p>
        </Card>
      </div>

      <Card className="p-0">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--line)] text-[var(--ink-muted)]">
              <th className="px-5 py-3 font-medium">Restoran</th>
              <th className="px-5 py-3 font-medium">Egasi</th>
              <th className="px-5 py-3 font-medium">Holat</th>
              <th className="px-5 py-3 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {restaurants.map((r) => (
              <tr key={r.id} className="border-b border-[var(--line)] last:border-0">
                <td className="px-5 py-3 font-medium">{r.name}</td>
                <td className="px-5 py-3 text-[var(--ink-muted)]">{r.user.username}</td>
                <td className="px-5 py-3">
                  <span className={r.is_active ? "text-green-600" : "text-red-500"}>
                    {r.is_active ? "Faol" : "To'xtatilgan"}
                  </span>
                </td>
                <td className="px-5 py-3 text-right">
                  <Button
                    variant={r.is_active ? "danger" : "secondary"}
                    onClick={() => toggleActive(r)}
                    disabled={togglingId === r.id}
                  >
                    {togglingId === r.id ? "..." : r.is_active ? "To'xtatish" : "Faollashtirish"}
                  </Button>
                </td>
              </tr>
            ))}
            {restaurants.length === 0 && (
              <tr>
                <td className="px-5 py-3 text-[var(--ink-muted)]" colSpan={4}>
                  Hozircha restoran yo&apos;q.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
