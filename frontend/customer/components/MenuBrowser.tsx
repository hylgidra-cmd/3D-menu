"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import FoodCard from "./FoodCard";
import { submitPublicOrder } from "@/lib/api";
import { formatPrice } from "@/lib/format";
import type { PaymentMethod, PublicCategory, PublicEat } from "@/lib/types";

const FoodDetailModal = dynamic(() => import("./FoodDetailModal"), { ssr: false });
type CartItem = { eat: PublicEat; quantity: number };
const paymentLabels: Record<PaymentMethod, string> = { cash: "Naqd", card: "Karta", online: "Onlayn" };

export default function MenuBrowser({ categories, token }: { categories: PublicCategory[]; token: string }) {
  const visibleCategories = categories.filter((c) => c.eats.length > 0);
  const [activeId, setActiveId] = useState(visibleCategories[0]?.id ?? null);
  const [selectedEat, setSelectedEat] = useState<PublicEat | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [checkout, setCheckout] = useState(false);
  const [payment, setPayment] = useState<PaymentMethod>("cash");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [successId, setSuccessId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const active = visibleCategories.find((c) => c.id === activeId) ?? visibleCategories[0];
  const total = useMemo(() => cart.reduce((sum, item) => sum + Number(item.eat.price) * item.quantity, 0), [cart]);
  const count = cart.reduce((sum, item) => sum + item.quantity, 0);

  const add = (eat: PublicEat) => { setCart((items) => { const found = items.find((i) => i.eat.id === eat.id); return found ? items.map((i) => i.eat.id === eat.id ? { ...i, quantity: i.quantity + 1 } : i) : [...items, { eat, quantity: 1 }]; }); setSelectedEat(null); };
  const setQuantity = (id: number, quantity: number) => setCart((items) => quantity < 1 ? items.filter((i) => i.eat.id !== id) : items.map((i) => i.eat.id === id ? { ...i, quantity } : i));
  const placeOrder = async () => { setSubmitting(true); setError(null); try { const order = await submitPublicOrder(token, cart.map((i) => ({ eat: i.eat.id, quantity: i.quantity })), payment, note); setSuccessId(order.id); setCart([]); setCheckout(false); setNote(""); } catch (err) { setError(err instanceof Error ? err.message : "Xatolik yuz berdi."); } finally { setSubmitting(false); } };

  if (visibleCategories.length === 0) return <p className="px-6 py-16 text-center text-sm text-[var(--ink-muted)]">Hozircha menyu bo&apos;sh.</p>;
  return <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col pb-24">
    <nav className="sticky top-0 z-10 flex gap-6 overflow-x-auto bg-[var(--bg)]/95 px-6 pt-6 pb-0 backdrop-blur">{visibleCategories.map((c) => <button key={c.id} onClick={() => setActiveId(c.id)} className={`shrink-0 whitespace-nowrap border-b-2 pb-3 text-[15px] font-medium ${c.id === active.id ? "border-[var(--brand)] text-[var(--ink)]" : "border-transparent text-[var(--ink-muted)]"}`}>{c.name}</button>)}</nav>
    <div className="h-px w-full bg-[var(--line)]" />
    <div key={active.id} className="animate-fade-in grid grid-cols-2 gap-x-3 gap-y-6 px-6 py-6 sm:grid-cols-3">{active.eats.map((eat) => <FoodCard key={eat.id} eat={eat} onSelect={() => setSelectedEat(eat)} />)}</div>
    {selectedEat && <FoodDetailModal eat={selectedEat} onClose={() => setSelectedEat(null)} onAdd={() => add(selectedEat)} />}
    {count > 0 && <button onClick={() => setCheckout(true)} className="fixed bottom-4 left-1/2 z-30 flex w-[min(480px,calc(100%-2rem))] -translate-x-1/2 items-center justify-between rounded-2xl bg-[var(--brand)] px-5 py-4 text-white shadow-xl"><span>🛍 Savat ({count})</span><strong>{formatPrice(String(total))}</strong></button>}
    {checkout && <div className="fixed inset-0 z-50 flex items-end bg-black/40 sm:items-center sm:justify-center" onClick={() => setCheckout(false)}><div className="w-full max-w-md rounded-t-3xl bg-[var(--surface)] p-6 sm:rounded-3xl" onClick={(e) => e.stopPropagation()}><div className="flex justify-between"><h2 className="text-lg font-bold">Buyurtmani tasdiqlash</h2><button onClick={() => setCheckout(false)}>×</button></div><div className="mt-4 max-h-44 space-y-2 overflow-y-auto">{cart.map((item) => <div key={item.eat.id} className="flex items-center justify-between text-sm"><span>{item.eat.name}</span><span className="flex items-center gap-2"><button onClick={() => setQuantity(item.eat.id, item.quantity - 1)}>−</button>{item.quantity}<button onClick={() => setQuantity(item.eat.id, item.quantity + 1)}>+</button></span></div>)}</div><p className="mt-4 font-bold">Jami: {formatPrice(String(total))}</p><p className="mt-4 text-sm font-medium">To&apos;lov usuli</p><div className="mt-2 grid grid-cols-3 gap-2">{(["cash", "card", "online"] as PaymentMethod[]).map((method) => <button key={method} onClick={() => setPayment(method)} className={`rounded-xl px-2 py-3 text-sm ${payment === method ? "bg-[var(--brand)] text-white" : "bg-[var(--bg)]"}`}>{paymentLabels[method]}</button>)}</div><textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Izoh (ixtiyoriy)" className="mt-4 w-full rounded-xl border border-[var(--line)] p-3 text-sm" rows={2} />{error && <p className="mt-2 text-sm text-red-600">{error}</p>}<button disabled={submitting || !cart.length} onClick={() => void placeOrder()} className="mt-4 w-full rounded-full bg-[var(--brand)] py-3 font-semibold text-white">{submitting ? "Yuborilmoqda..." : "Buyurtma berish"}</button><p className="mt-2 text-center text-xs text-[var(--ink-muted)]">Onlayn to&apos;lov provayderi keyingi bosqichda ulanadi.</p></div></div>}
    {successId && <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4"><div className="w-full max-w-sm rounded-3xl bg-white p-6 text-center"><h2 className="text-xl font-bold">Buyurtma qabul qilindi</h2><p className="mt-2 text-sm text-[var(--ink-muted)]">Buyurtma raqami: #{successId}. Ofitsiant tez orada qabul qiladi.</p><button onClick={() => setSuccessId(null)} className="mt-5 rounded-full bg-[var(--brand)] px-5 py-3 text-sm font-semibold text-white">Davom etish</button></div></div>}
  </div>;
}
