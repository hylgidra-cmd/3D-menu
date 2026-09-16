"use client";

import { useEffect, useMemo, useState, type DragEvent, type FormEvent } from "react";
import { CakeSlice, CupSoda, Eye, EyeOff, GripVertical, Pencil, Plus, Salad, Search, Trash2, UtensilsCrossed, X, type LucideIcon } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { useRestaurant } from "@/lib/restaurant";
import { Button, ErrorText, Field, Input } from "@/components/ui";
import type { Category } from "@/lib/types";

type Filter = "all" | "active" | "hidden";

const CATEGORY_ICONS: { value: string; label: string; Icon: LucideIcon }[] = [
  { value: "utensils", label: "Taomlar", Icon: UtensilsCrossed },
  { value: "drink", label: "Ichimliklar", Icon: CupSoda },
  { value: "dessert", label: "Desertlar", Icon: CakeSlice },
  { value: "salad", label: "Salatlar", Icon: Salad },
];
const DEFAULT_ICON = CATEGORY_ICONS[0].value;

function CategoryIcon({ icon, size = 22 }: { icon: string; size?: number }) {
  const Icon = CATEGORY_ICONS.find((item) => item.value === icon)?.Icon ?? UtensilsCrossed;
  return <Icon size={size} strokeWidth={1.8} />;
}

export default function CategoriesPage() {
  const { current, loading: restaurantLoading } = useRestaurant();
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Category | null>(null);
  const [name, setName] = useState("");
  const [order, setOrder] = useState(1);
  const [icon, setIcon] = useState(DEFAULT_ICON);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState<Category | null>(null);
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [reordering, setReordering] = useState(false);

  const load = async () => {
    if (!current) return;
    setLoading(true);
    try {
      const data = await apiFetch<{ results: Category[] }>(`/api/eat/category/?restaurant=${current.id}`);
      setCategories(data.results);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kategoriyalarni yuklab bo'lmadi.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reload when the selected restaurant changes
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current]);

  const filteredCategories = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return categories.filter((category) => {
      const matchesSearch = !query || category.name.toLocaleLowerCase().includes(query);
      const matchesFilter = filter === "all" || (filter === "active" ? category.is_active : !category.is_active);
      return matchesSearch && matchesFilter;
    });
  }, [categories, filter, search]);

  const canReorder = filter === "all" && !search.trim() && !reordering;

  const openCreate = () => {
    setEditing(null);
    setName("");
    setIcon(DEFAULT_ICON);
    setOrder(Math.max(0, ...categories.map((category) => category.order)) + 1);
    setError(null);
    setModalOpen(true);
  };

  const openEdit = (category: Category) => {
    setEditing(category);
    setName(category.name);
    setIcon(CATEGORY_ICONS.some((item) => item.value === category.icon) ? category.icon : DEFAULT_ICON);
    setOrder(category.order);
    setError(null);
    setModalOpen(true);
  };

  const closeModal = () => {
    if (!submitting) {
      setModalOpen(false);
      setEditing(null);
    }
  };

  const saveCategory = async (event: FormEvent) => {
    event.preventDefault();
    if (!current || !name.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload = { name: name.trim(), icon, order: Math.max(0, Number(order) || 0) };
      if (editing) {
        await apiFetch(`/api/eat/category/${editing.id}/`, { method: "PATCH", body: JSON.stringify(payload) });
      } else {
        await apiFetch("/api/eat/category/", { method: "POST", body: JSON.stringify({ ...payload, restaurant: current.id }) });
      }
      await load();
      setModalOpen(false);
      setEditing(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kategoriyani saqlab bo'lmadi.");
    } finally {
      setSubmitting(false);
    }
  };

  const toggleActive = async (category: Category) => {
    setError(null);
    try {
      await apiFetch(`/api/eat/category/${category.id}/`, { method: "PATCH", body: JSON.stringify({ is_active: !category.is_active }) });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Holatni o'zgartirib bo'lmadi.");
    }
  };

  const removeCategory = async () => {
    if (!deleting) return;
    try {
      await apiFetch(`/api/eat/category/${deleting.id}/`, { method: "DELETE" });
      setDeleting(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kategoriyani o'chirib bo'lmadi.");
      setDeleting(null);
    }
  };

  const reorder = async (targetId: number) => {
    if (draggedId === null || draggedId === targetId || !canReorder) return;
    const from = categories.findIndex((category) => category.id === draggedId);
    const to = categories.findIndex((category) => category.id === targetId);
    if (from < 0 || to < 0) return;
    const next = [...categories];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    const ordered = next.map((category, index) => ({ ...category, order: index + 1 }));
    setCategories(ordered);
    setDraggedId(null);
    setReordering(true);
    try {
      await Promise.all(ordered.map((category) => apiFetch(`/api/eat/category/${category.id}/`, {
        method: "PATCH", body: JSON.stringify({ order: category.order }),
      })));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Tartibni saqlab bo'lmadi.");
      await load();
    } finally {
      setReordering(false);
    }
  };

  const onDragStart = (event: DragEvent<HTMLDivElement>, id: number) => {
    if (!canReorder) return;
    event.dataTransfer.effectAllowed = "move";
    setDraggedId(id);
  };

  if (restaurantLoading) return <p className="text-sm text-[var(--ink-muted)]">Yuklanmoqda...</p>;
  if (!current) return <p className="text-sm text-[var(--ink-muted)]">Avval restoran yarating.</p>;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-col gap-4 border-b border-[var(--line)] pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--ink)]">Kategoriyalar</h1>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">Taomlarni tartibli ko&apos;rsatish uchun kategoriyalarni boshqaring</p>
        </div>
        <Button onClick={openCreate} className="w-full sm:w-auto"><Plus size={17} strokeWidth={2.5} /> Yangi kategoriya</Button>
      </header>

      <div className="flex flex-col gap-3 rounded-2xl bg-[var(--surface)] p-3 ring-1 ring-[var(--line)] sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-sm">
          <Search size={17} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--ink-muted)]" />
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Kategoriya qidirish..." className="w-full pl-10" />
        </div>
        <div className="grid grid-cols-3 rounded-xl bg-[var(--bg)] p-1 text-sm sm:flex">
          {(["all", "active", "hidden"] as Filter[]).map((value) => {
            const labels: Record<Filter, string> = { all: "Barchasi", active: "Faol", hidden: "Yashirilgan" };
            return <button key={value} onClick={() => setFilter(value)} className={`rounded-lg px-3 py-2 font-medium transition ${filter === value ? "bg-[var(--surface)] text-[var(--ink)] shadow-sm" : "text-[var(--ink-muted)] hover:text-[var(--ink)]"}`}>{labels[value]}</button>;
          })}
        </div>
      </div>

      <ErrorText>{error}</ErrorText>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">{[1, 2, 3].map((item) => <div key={item} className="h-44 animate-pulse rounded-2xl bg-[var(--surface)] ring-1 ring-[var(--line)]" />)}</div>
      ) : categories.length === 0 ? (
        <div className="flex min-h-72 flex-col items-center justify-center rounded-3xl border border-dashed border-[var(--line)] bg-[var(--surface)] px-6 text-center">
          <span className="grid h-14 w-14 place-items-center rounded-2xl bg-[var(--bg)] text-[var(--ink)]"><UtensilsCrossed size={25} /></span>
          <h2 className="mt-4 text-lg font-bold text-[var(--ink)]">Hozircha kategoriyalar mavjud emas</h2>
          <p className="mt-1 max-w-sm text-sm text-[var(--ink-muted)]">Menyudagi taomlarni guruhlash uchun birinchi kategoriyani yarating.</p>
          <Button onClick={openCreate} className="mt-5"><Plus size={16} /> Birinchi kategoriyani yarating</Button>
        </div>
      ) : filteredCategories.length === 0 ? (
        <div className="rounded-3xl bg-[var(--surface)] px-6 py-14 text-center ring-1 ring-[var(--line)]"><Search size={24} className="mx-auto text-[var(--ink-muted)]" /><p className="mt-3 font-medium text-[var(--ink)]">Mos kategoriya topilmadi</p><button onClick={() => { setSearch(""); setFilter("all"); }} className="mt-2 text-sm font-medium underline underline-offset-4">Filtrlarni tozalash</button></div>
      ) : (
        <>
          <p className="-mt-2 text-xs text-[var(--ink-muted)]">{canReorder ? "Kartochkani ushlab joyini o'zgartiring — tartib avtomatik saqlanadi." : "Drag-and-drop uchun qidiruv va filtrlarni tozalang."}</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredCategories.map((category) => (
              <div key={category.id} draggable={canReorder} onDragStart={(event) => onDragStart(event, category.id)} onDragOver={(event) => { if (canReorder) event.preventDefault(); }} onDrop={() => void reorder(category.id)} onDragEnd={() => setDraggedId(null)} className={`group relative rounded-2xl border bg-[var(--surface)] p-4 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-md ${draggedId === category.id ? "border-[var(--ink)]/30 opacity-50" : "border-[var(--line)]"} ${canReorder ? "cursor-grab active:cursor-grabbing" : ""}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3"><span className="hidden text-[var(--ink-muted)] sm:block"><GripVertical size={18} /></span><span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[var(--bg)] text-[var(--ink)]" aria-hidden><CategoryIcon icon={category.icon} /></span><div className="min-w-0"><h2 className="truncate font-bold text-[var(--ink)]">{category.name}</h2><p className="mt-0.5 text-xs text-[var(--ink-muted)]">{category.eats_count} ta taom</p></div></div>
                  <div className="flex shrink-0 items-center gap-1"><button onClick={() => openEdit(category)} aria-label="Tahrirlash" className="grid h-8 w-8 place-items-center rounded-lg text-[var(--ink-muted)] transition hover:bg-[var(--bg)] hover:text-[var(--ink)]"><Pencil size={16} /></button><button onClick={() => setDeleting(category)} aria-label="O'chirish" className="grid h-8 w-8 place-items-center rounded-lg text-[var(--ink-muted)] transition hover:bg-red-50 hover:text-red-600"><Trash2 size={16} /></button></div>
                </div>
                <div className="mt-5 flex items-center justify-between gap-2 border-t border-[var(--line)] pt-3"><span className="rounded-full bg-[var(--bg)] px-2.5 py-1 text-xs font-medium text-[var(--ink-muted)]">Tartib: {category.order}</span><button onClick={() => void toggleActive(category)} className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold transition ${category.is_active ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100" : "bg-stone-100 text-stone-600 hover:bg-stone-200"}`}>{category.is_active ? <Eye size={14} /> : <EyeOff size={14} />}{category.is_active ? "Faol" : "Yashirilgan"}</button></div>
              </div>
            ))}
          </div>
        </>
      )}

      {modalOpen && (
        <div className="fixed inset-0 z-50 grid place-items-center p-4" role="dialog" aria-modal="true" aria-labelledby="category-modal-title" onMouseDown={closeModal}>
          <div className="absolute inset-0 bg-black/35" />
          <form onSubmit={saveCategory} onMouseDown={(event) => event.stopPropagation()} className="animate-menu-drop relative w-full max-w-md rounded-3xl bg-[var(--surface)] p-5 shadow-2xl sm:p-6">
            <div className="mb-5 flex items-start justify-between gap-4"><div><h2 id="category-modal-title" className="text-lg font-bold text-[var(--ink)]">{editing ? "Kategoriyani tahrirlash" : "Yangi kategoriya"}</h2><p className="mt-1 text-sm text-[var(--ink-muted)]">Kategoriya ma&apos;lumotlarini kiriting.</p></div><button type="button" onClick={closeModal} aria-label="Yopish" className="grid h-9 w-9 place-items-center rounded-xl text-[var(--ink-muted)] ring-1 ring-[var(--line)] hover:bg-[var(--bg)]"><X size={18} /></button></div>
            <div className="flex flex-col gap-4"><Field label="Kategoriya nomi"><Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Masalan, Ichimliklar" maxLength={100} required autoFocus /></Field><Field label="Ko'rinish tartibi"><Input type="number" value={order} onChange={(event) => setOrder(Number(event.target.value))} min={0} /></Field><div><p className="mb-2 text-sm font-medium text-[var(--ink)]">Kategoriya iconi</p><div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{CATEGORY_ICONS.map(({ value, label, Icon }) => <button key={value} type="button" onClick={() => setIcon(value)} aria-label={`${label} iconini tanlash`} className={`flex min-h-20 flex-col items-center justify-center gap-1.5 rounded-xl text-sm font-medium transition ${icon === value ? "bg-[var(--ink)] text-white ring-2 ring-[var(--ink)] ring-offset-2" : "bg-[var(--bg)] text-[var(--ink)] hover:bg-stone-200"}`}><Icon size={22} strokeWidth={1.8} /><span>{label}</span></button>)}</div><p className="mt-2 text-xs text-[var(--ink-muted)]">Taomlar, Ichimliklar, Desertlar yoki Salatlar uchun icon tanlang.</p></div><ErrorText>{error}</ErrorText><div className="mt-1 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><Button type="button" variant="secondary" onClick={closeModal}>Bekor qilish</Button><Button type="submit" disabled={submitting}>{submitting ? "Saqlanmoqda..." : "Saqlash"}</Button></div></div>
          </form>
        </div>
      )}

      {deleting && (
        <div className="fixed inset-0 z-50 grid place-items-center p-4" role="dialog" aria-modal="true" aria-labelledby="delete-modal-title" onMouseDown={() => setDeleting(null)}><div className="absolute inset-0 bg-black/35" /><div onMouseDown={(event) => event.stopPropagation()} className="animate-menu-drop relative w-full max-w-sm rounded-3xl bg-[var(--surface)] p-6 shadow-2xl"><span className="grid h-11 w-11 place-items-center rounded-2xl bg-red-50 text-red-600"><Trash2 size={20} /></span><h2 id="delete-modal-title" className="mt-4 text-lg font-bold text-[var(--ink)]">Ushbu kategoriyani o&apos;chirmoqchimisiz?</h2>{deleting.eats_count > 0 ? <p className="mt-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-800"><strong>{deleting.eats_count} ta taom</strong> ushbu kategoriyaga biriktirilgan. O&apos;chirilganda ulardagi kategoriya bo&apos;sh qoladi.</p> : <p className="mt-2 text-sm text-[var(--ink-muted)]">Bu amalni keyin qaytarib bo&apos;lmaydi.</p>}<div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><Button variant="secondary" onClick={() => setDeleting(null)}>Bekor qilish</Button><Button variant="danger" onClick={() => void removeCategory()}>O&apos;chirish</Button></div></div></div>
      )}
    </div>
  );
}
