"use client";

import { useCallback, useEffect, useState } from "react";
import { ClipboardList } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useRestaurant } from "@/lib/restaurant";
import { formatPrice } from "@/lib/format";
import type { Order } from "@/lib/types";

const labels: Record<string, string> = {
  new: "Yangi",
  accepted: "Qabul qilindi",
  preparing: "Tayyorlanmoqda",
  ready: "Tayyor",
  served: "Yetkazildi",
  cancelled: "Bekor qilindi",
};
const statuses = ["new", "accepted", "preparing", "ready", "served", "cancelled"];

export default function OrdersPage() {
  const { current, loading } = useRestaurant();
  const [orders, setOrders] = useState<Order[]>([]);
  const [busy, setBusy] = useState<number | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const load = useCallback(async () => {
    if (!current) return;
    const data = await apiFetch<{ results: Order[] }>(`/api/orders/?restaurant=${current.id}`);
    setOrders(data.results);
    setUpdatedAt(new Date());
  }, [current]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") void load();
    };
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [load]);

  const update = async (order: Order, status: string) => {
    setBusy(order.id);
    try {
      await apiFetch(`/api/orders/${order.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      await load();
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <p>Yuklanmoqda...</p>;
  if (!current) return null;

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6 border-b border-[var(--line)] pb-5">
        <h1 className="text-2xl font-bold">Buyurtmalar</h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">Stollardan kelgan buyurtmalar avtomatik yangilanadi.</p>
        <p className="mt-2 text-xs text-[var(--ink-muted)]" aria-live="polite">
          {updatedAt ? `Oxirgi yangilanish: ${updatedAt.toLocaleTimeString("uz-UZ")}` : "Yangilanmoqda..."}
        </p>
      </header>

      {orders.length === 0 ? (
        <div className="rounded-3xl bg-[var(--surface)] py-16 text-center ring-1 ring-[var(--line)]">
          <ClipboardList className="mx-auto text-[var(--ink-muted)]" />
          <p className="mt-3 font-medium">Hozircha buyurtmalar yo&apos;q</p>
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map((order) => (
            <div key={order.id} className="rounded-2xl bg-[var(--surface)] p-5 ring-1 ring-[var(--line)]">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-bold">Buyurtma #{order.id} · Stol {order.table_name}</p>
                  <p className="mt-1 text-sm text-[var(--ink-muted)]">
                    {order.items.map((item) => `${item.name} × ${item.quantity}`).join(", ")}
                  </p>
                  {order.note && <p className="mt-2 text-sm">Izoh: {order.note}</p>}
                </div>
                <p className="text-right font-bold">{formatPrice(order.total)}</p>
              </div>
              <select
                disabled={busy === order.id}
                value={order.status}
                onChange={(event) => void update(order, event.target.value)}
                className="mt-4 rounded-xl border border-[var(--line)] px-3 py-2 text-sm"
              >
                {statuses.map((status) => <option key={status} value={status}>{labels[status]}</option>)}
              </select>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
