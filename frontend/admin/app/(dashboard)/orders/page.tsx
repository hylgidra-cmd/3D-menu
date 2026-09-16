"use client";
import { useEffect, useState } from "react";
import { ClipboardList } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useRestaurant } from "@/lib/restaurant";
import { formatPrice } from "@/lib/format";
import type { Order } from "@/lib/types";

const labels: Record<string, string> = { new: "Yangi", accepted: "Qabul qilindi", preparing: "Tayyorlanmoqda", ready: "Tayyor", served: "Yetkazildi", cancelled: "Bekor qilindi", cash: "Naqd", card: "Karta", online: "Onlayn" };
const statuses = ["new", "accepted", "preparing", "ready", "served", "cancelled"];
export default function OrdersPage() {
  const { current, loading } = useRestaurant(); const [orders, setOrders] = useState<Order[]>([]); const [busy, setBusy] = useState<number | null>(null);
  const load = async () => { if (current) setOrders((await apiFetch<{ results: Order[] }>(`/api/orders/?restaurant=${current.id}`)).results); };
  useEffect(() => { void load(); }, [current]);
  const update = async (order: Order, status: string) => { setBusy(order.id); await apiFetch(`/api/orders/${order.id}/`, { method: "PATCH", body: JSON.stringify({ status }) }); await load(); setBusy(null); };
  if (loading) return <p>Yuklanmoqda...</p>; if (!current) return null;
  return <div className="mx-auto max-w-5xl"><header className="mb-6 border-b border-[var(--line)] pb-5"><h1 className="text-2xl font-bold">Buyurtmalar</h1><p className="mt-1 text-sm text-[var(--ink-muted)]">Stollardan kelgan buyurtmalarni boshqaring.</p></header>{orders.length === 0 ? <div className="rounded-3xl bg-[var(--surface)] py-16 text-center ring-1 ring-[var(--line)]"><ClipboardList className="mx-auto text-[var(--ink-muted)]" /><p className="mt-3 font-medium">Hozircha buyurtmalar yo&apos;q</p></div> : <div className="space-y-3">{orders.map((order) => <div key={order.id} className="rounded-2xl bg-[var(--surface)] p-5 ring-1 ring-[var(--line)]"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-bold">Buyurtma #{order.id} · Stol {order.table_name}</p><p className="mt-1 text-sm text-[var(--ink-muted)]">{order.items.map((i) => `${i.name} × ${i.quantity}`).join(", ")}</p>{order.note && <p className="mt-2 text-sm">Izoh: {order.note}</p>}</div><div className="text-right"><p className="font-bold">{formatPrice(order.total)}</p><p className="mt-1 text-sm text-[var(--ink-muted)]">{labels[order.payment_method]}</p></div></div><select disabled={busy === order.id} value={order.status} onChange={(e) => void update(order, e.target.value)} className="mt-4 rounded-xl border border-[var(--line)] px-3 py-2 text-sm">{statuses.map((s) => <option key={s} value={s}>{labels[s]}</option>)}</select></div>)}</div>}</div>;
}
