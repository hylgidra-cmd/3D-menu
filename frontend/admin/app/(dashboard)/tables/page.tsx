"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiFetch, resolveMediaUrl, ApiError } from "@/lib/api";
import { useRestaurant } from "@/lib/restaurant";
import { Button, Card, ErrorText, Field, Input } from "@/components/ui";
import type { Table } from "@/lib/types";

export default function TablesPage() {
  const { current, loading: restaurantLoading } = useRestaurant();
  const [tables, setTables] = useState<Table[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [place, setPlace] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const load = async () => {
    if (!current) return;
    setLoading(true);
    const data = await apiFetch<{ results: Table[] }>(`/api/table/?restaurant=${current.id}`);
    setTables(data.results);
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
      await apiFetch("/api/table/", {
        method: "POST",
        body: JSON.stringify({ restaurant: current.id, name, place }),
      });
      setName("");
      setPlace("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Xatolik yuz berdi.");
    }
  };

  const remove = async (table: Table) => {
    if (!confirm(`Stol "${table.name}" o'chirilsinmi? QR kod ishlamay qoladi.`)) return;
    await apiFetch(`/api/table/${table.id}/`, { method: "DELETE" });
    await load();
  };

  const copyLink = async (table: Table) => {
    await navigator.clipboard.writeText(table.menu_url);
    setCopiedId(table.id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  if (restaurantLoading) return <p className="text-sm text-[var(--ink-muted)]">Yuklanmoqda...</p>;
  if (!current) return <p className="text-sm text-[var(--ink-muted)]">Avval restoran yarating.</p>;

  return (
    <div className="flex max-w-3xl flex-col gap-4">
      <h1 className="text-lg font-bold text-[var(--ink)]">Stollar / QR kodlar</h1>

      <Card>
        <form onSubmit={onCreate} className="flex items-end gap-2">
          <Field label="Stol nomi">
            <Input value={name} onChange={(e) => setName(e.target.value)} required placeholder="A1" />
          </Field>
          <Field label="Joylashuv">
            <Input value={place} onChange={(e) => setPlace(e.target.value)} placeholder="Zal" />
          </Field>
          <Button type="submit">Qo&apos;shish</Button>
        </form>
        <ErrorText>{error}</ErrorText>
      </Card>

      {loading ? (
        <p className="text-sm text-[var(--ink-muted)]">Yuklanmoqda...</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
          {tables.map((table) => {
            const qrUrl = resolveMediaUrl(table.qr_code);
            return (
              <Card key={table.id} className="flex flex-col items-center gap-2 p-3 text-center">
                {qrUrl && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={qrUrl} alt={`QR - ${table.name}`} className="h-32 w-32" />
                )}
                <p className="text-sm font-semibold">
                  {table.name}
                  {table.place ? ` · ${table.place}` : ""}
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  <Button variant="secondary" onClick={() => copyLink(table)}>
                    {copiedId === table.id ? "Nusxalandi!" : "Havolani nusxalash"}
                  </Button>
                  <a href={qrUrl ?? "#"} download={`stol-${table.name}.png`}>
                    <Button variant="secondary" type="button">
                      Yuklab olish
                    </Button>
                  </a>
                  <Button variant="danger" onClick={() => remove(table)}>
                    O&apos;chirish
                  </Button>
                </div>
              </Card>
            );
          })}
          {tables.length === 0 && <p className="text-sm text-[var(--ink-muted)]">Hozircha stol yo&apos;q.</p>}
        </div>
      )}
    </div>
  );
}
