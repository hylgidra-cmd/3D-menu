"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { useRestaurant } from "@/lib/restaurant";
import { Button, Card, ErrorText, Field, Input } from "@/components/ui";
import type { Category } from "@/lib/types";

export default function CategoriesPage() {
  const { current, loading: restaurantLoading } = useRestaurant();
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [order, setOrder] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!current) return;
    setLoading(true);
    const data = await apiFetch<{ results: Category[] }>(`/api/eat/category/?restaurant=${current.id}`);
    setCategories(data.results);
    setLoading(false);
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reload when the selected restaurant changes
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current]);

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!current) return;
    setError(null);
    try {
      await apiFetch("/api/eat/category/", {
        method: "POST",
        body: JSON.stringify({ restaurant: current.id, name, order }),
      });
      setName("");
      setOrder(0);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Xatolik yuz berdi.");
    }
  };

  const toggleActive = async (c: Category) => {
    await apiFetch(`/api/eat/category/${c.id}/`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !c.is_active }),
    });
    await load();
  };

  const remove = async (c: Category) => {
    if (!confirm(`"${c.name}" kategoriyasini o'chirasizmi?`)) return;
    await apiFetch(`/api/eat/category/${c.id}/`, { method: "DELETE" });
    await load();
  };

  if (restaurantLoading) return <p className="text-sm text-[var(--ink-muted)]">Yuklanmoqda...</p>;
  if (!current) return <p className="text-sm text-[var(--ink-muted)]">Avval restoran yarating.</p>;

  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <h1 className="text-lg font-bold text-[var(--ink)]">Kategoriyalar</h1>

      <Card>
        <form onSubmit={onCreate} className="flex items-end gap-2">
          <Field label="Nomi">
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label="Tartib">
            <Input type="number" value={order} onChange={(e) => setOrder(Number(e.target.value))} className="w-20" />
          </Field>
          <Button type="submit">Qo&apos;shish</Button>
        </form>
        <ErrorText>{error}</ErrorText>
      </Card>

      {loading ? (
        <p className="text-sm text-[var(--ink-muted)]">Yuklanmoqda...</p>
      ) : (
        <Card className="p-0">
          <ul className="divide-y divide-[var(--line)]">
            {categories.map((c) => (
              <li key={c.id} className="flex items-center justify-between px-5 py-3">
                <span className={c.is_active ? "" : "text-[var(--ink-muted)] line-through"}>{c.name}</span>
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => toggleActive(c)}>
                    {c.is_active ? "Yashirish" : "Ko'rsatish"}
                  </Button>
                  <Button variant="danger" onClick={() => remove(c)}>
                    O&apos;chirish
                  </Button>
                </div>
              </li>
            ))}
            {categories.length === 0 && (
              <li className="px-5 py-3 text-sm text-[var(--ink-muted)]">Kategoriya yo&apos;q.</li>
            )}
          </ul>
        </Card>
      )}
    </div>
  );
}
