"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ImagePlus, MapPin, Store } from "lucide-react";
import { apiFetch, resolveMediaUrl, ApiError } from "@/lib/api";
import { useRestaurant } from "@/lib/restaurant";
import { Button, Card, ErrorText, Field, Input, Textarea } from "@/components/ui";
import type { Restaurant } from "@/lib/types";

export default function RestaurantProfilePage() {
  const { current, loading, refresh } = useRestaurant();
  const router = useRouter();
  const isNew = !loading && !current;

  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!current) return;
    apiFetch<Restaurant>(`/api/restaurant/${current.id}/`).then((r) => {
      setRestaurant(r);
      setName(r.name);
      setDescription(r.description ?? "");
      setLocation(r.location ?? "");
    });
  }, [current]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("name", name);
      form.append("description", description);
      form.append("location", location);
      if (logoFile) form.append("logo", logoFile);
      if (coverFile) form.append("cover_image", coverFile);

      if (restaurant) {
        await apiFetch(`/api/restaurant/${restaurant.id}/`, { method: "PATCH", body: form, isForm: true });
      } else {
        await apiFetch("/api/restaurant/", { method: "POST", body: form, isForm: true });
      }
      await refresh();
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Saqlashda xatolik yuz berdi.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p className="text-sm text-[var(--ink-muted)]">Yuklanmoqda...</p>;

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header className="border-b border-[var(--line)] pb-5">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-2xl bg-[var(--ink)] text-white"><Store size={20} /></span>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-[var(--ink)]">{isNew ? "Restoraningizni yarating" : "Restoran profili"}</h1>
            <p className="mt-1 text-sm text-[var(--ink-muted)]">Restoran haqidagi asosiy ma&apos;lumotlar va rasmlarni boshqaring.</p>
          </div>
        </div>
      </header>

      <form onSubmit={onSubmit} className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Card className="flex flex-col gap-5 lg:col-span-2">
          <div>
            <h2 className="font-bold text-[var(--ink)]">Asosiy ma&apos;lumotlar</h2>
            <p className="mt-1 text-sm text-[var(--ink-muted)]">Bu ma&apos;lumotlar mijozlar ko&apos;radigan menyuda chiqadi.</p>
          </div>
          <Field label="Restoran nomi">
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Masalan, Osh markazi" required minLength={3} />
          </Field>
          <Field label="Tavsif">
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Restoraningiz haqida qisqacha yozing" rows={5} />
          </Field>
          <Field label="Manzil">
            <div className="relative"><MapPin size={17} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--ink-muted)]" /><Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Toshkent, ..." className="w-full pl-10" /></div>
          </Field>
        </Card>

        <Card className="flex flex-col gap-5">
          <div>
            <h2 className="font-bold text-[var(--ink)]">Rasmlar</h2>
            <p className="mt-1 text-sm text-[var(--ink-muted)]">Logotip va muqova rasmini yangilang.</p>
          </div>
          <Field label="Logotip">
            <Input type="file" accept="image/*" onChange={(e) => setLogoFile(e.target.files?.[0] ?? null)} />
            {restaurant?.logo && !logoFile ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={resolveMediaUrl(restaurant.logo) ?? ""} alt="Restoran logotipi" className="mt-2 h-20 w-20 rounded-2xl object-cover ring-1 ring-[var(--line)]" />
            ) : <span className="mt-2 grid h-20 w-20 place-items-center rounded-2xl bg-[var(--bg)] text-[var(--ink-muted)]"><ImagePlus size={22} /></span>}
          </Field>
          <Field label="Muqova rasmi">
            <Input type="file" accept="image/*" onChange={(e) => setCoverFile(e.target.files?.[0] ?? null)} />
            {restaurant?.cover_image && !coverFile ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={resolveMediaUrl(restaurant.cover_image) ?? ""} alt="Restoran muqovasi" className="mt-2 aspect-[2/1] w-full rounded-2xl object-cover ring-1 ring-[var(--line)]" />
            ) : <span className="mt-2 grid aspect-[2/1] w-full place-items-center rounded-2xl bg-[var(--bg)] text-[var(--ink-muted)]"><ImagePlus size={22} /></span>}
          </Field>
        </Card>

        <div className="flex flex-col gap-3 lg:col-span-3">
          <ErrorText>{error}</ErrorText>
          <div className="flex justify-end"><Button type="submit" disabled={submitting} className="w-full sm:w-auto">{submitting ? "Saqlanmoqda..." : "O'zgarishlarni saqlash"}</Button></div>
        </div>
      </form>
    </div>
  );
}
