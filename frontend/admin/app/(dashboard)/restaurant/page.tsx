"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
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
  const [primaryColor, setPrimaryColor] = useState("#111827");
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
      setPrimaryColor(r.primary_color);
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
      form.append("primary_color", primaryColor);
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
    <div className="max-w-lg">
      <h1 className="mb-4 text-lg font-bold text-[var(--ink)]">
        {isNew ? "Restoraningizni yarating" : "Restoran profili"}
      </h1>
      <Card>
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <Field label="Nomi">
            <Input value={name} onChange={(e) => setName(e.target.value)} required minLength={3} />
          </Field>
          <Field label="Tavsif">
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
          </Field>
          <Field label="Manzil">
            <Input value={location} onChange={(e) => setLocation(e.target.value)} />
          </Field>
          <Field label="Brend rangi">
            <Input type="color" value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)} className="h-10 w-20 p-1" />
          </Field>
          <Field label="Logotip">
            <Input type="file" accept="image/*" onChange={(e) => setLogoFile(e.target.files?.[0] ?? null)} />
            {restaurant?.logo && !logoFile && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={resolveMediaUrl(restaurant.logo) ?? ""} alt="" className="mt-1 h-12 w-12 rounded-lg object-cover" />
            )}
          </Field>
          <Field label="Muqova rasmi">
            <Input type="file" accept="image/*" onChange={(e) => setCoverFile(e.target.files?.[0] ?? null)} />
          </Field>
          <ErrorText>{error}</ErrorText>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Saqlanmoqda..." : "Saqlash"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
