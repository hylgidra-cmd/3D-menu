"use client";

import { useEffect, useState, type FormEvent } from "react";
import dynamic from "next/dynamic";
import { Pencil, Plus, X } from "lucide-react";
import { apiFetch, resolveMediaUrl, ApiError, AuthenticationError } from "@/lib/api";
import { useRestaurant } from "@/lib/restaurant";
import { formatPrice } from "@/lib/format";
import { Button, Card, ErrorText, Field, Input, Textarea } from "@/components/ui";
import type { Category, Eat } from "@/lib/types";

// model-viewer touches browser globals at module load time, so it must
// never be evaluated during SSR.
const Model3DPreview = dynamic(() => import("@/components/Model3DPreview"), { ssr: false });

const STATUS_LABELS: Record<string, string> = {
  pending: "navbatda",
  in_progress: "yaratilmoqda...",
  processing: "yaratilmoqda...",
  finished: "tayyor",
  downloading: "saqlanmoqda...",
  failed: "xatolik yuz berdi",
  unknown: "noma'lum",
};

const MODEL_ERROR_LABELS: Record<string, string> = {
  AUTH_ERROR: "3D API token noto'g'ri yoki amal qilmayapti.",
  INSUFFICIENT_CREDITS: "3D API krediti tugagan.",
  TASK_ACCESS_DENIED: "Bu 3D task boshqa API akkauntiga tegishli.",
  TASK_NOT_FOUND: "3D task topilmadi. Modelni qayta generatsiya qilish kerak.",
  RATE_LIMITED: "3D servis limiti vaqtincha tugagan. Keyinroq qayta urinib ko'ring.",
  PROVIDER_ERROR: "3D servisda xatolik yuz berdi.",
  NETWORK_ERROR: "3D servisga ulanib bo'lmadi. Keyinroq qayta urinib ko'ring.",
};

function modelErrorLabel(eat: Eat) {
  if (eat.model_error_type && MODEL_ERROR_LABELS[eat.model_error_type]) {
    return MODEL_ERROR_LABELS[eat.model_error_type];
  }
  return eat.model_error ?? "3D modelda xatolik yuz berdi.";
}

function modelStatusLabel(status: string) {
  return STATUS_LABELS[status] ?? status;
}

const USDZ_STATUS_LABELS: Record<string, string> = {
  pending: "navbatda",
  ready: "tayyor",
  failed: "xatolik yuz berdi",
};

function usdzErrorLabel(eat: Eat) {
  if (eat.usdz_error_type && MODEL_ERROR_LABELS[eat.usdz_error_type]) {
    return MODEL_ERROR_LABELS[eat.usdz_error_type];
  }
  return eat.usdz_error ?? "iOS uchun 3D faylni tayyorlab bo'lmadi.";
}

export default function MenuPage() {
  const { current, loading: restaurantLoading } = useRestaurant();
  const [eats, setEats] = useState<Eat[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [categoryId, setCategoryId] = useState<string>("");
  const [image, setImage] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingEat, setEditingEat] = useState<Eat | null>(null);

  const load = async () => {
    if (!current) return;
    setLoading(true);
    const [eatsData, categoriesData] = await Promise.all([
      apiFetch<{ results: Eat[] }>(`/api/eat/?restaurant=${current.id}`),
      apiFetch<{ results: Category[] }>(`/api/eat/category/?restaurant=${current.id}`),
    ]);
    setEats(eatsData.results);
    setCategories(categoriesData.results);
    setLoading(false);
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reload when the selected restaurant changes
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current]);

  // Auto-poll 3D model status for anything still generating, so the admin
  // doesn't have to keep clicking "Tekshirish" by hand. Re-schedules itself
  // (via the `eats` dependency) after every poll, and simply stops
  // re-scheduling once nothing is pending anymore.
  useEffect(() => {
    const pending = eats.filter((e) => !e.model_url && !e.model_error);
    if (!current || pending.length === 0) return;

    const timer = setTimeout(async () => {
      await Promise.all(
        pending.map((e) => apiFetch(`/api/eat/check-model/${e.id}/`).catch(() => undefined))
      );
      const data = await apiFetch<{ results: Eat[] }>(`/api/eat/?restaurant=${current.id}`);
      setEats(data.results);
    }, 10000);

    return () => clearTimeout(timer);
  }, [eats, current]);

  const resetForm = () => {
    setName("");
    setDescription("");
    setPrice("");
    setCategoryId("");
    setImage(null);
  };

  const onSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!current || (!image && !editingEat)) return;
    setError(null);
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("restaurant", String(current.id));
      form.append("name", name);
      form.append("description", description);
      form.append("price", price);
      if (editingEat) {
        // Send an empty value when the existing category is deliberately cleared.
        form.append("category", categoryId);
        if (image) form.append("image", image);
        await apiFetch(`/api/eat/${editingEat.id}/`, { method: "PATCH", body: form, isForm: true });
      } else {
        if (categoryId) form.append("category", categoryId);
        form.append("image", image!);
        await apiFetch("/api/eat/", { method: "POST", body: form, isForm: true });
      }
      resetForm();
      setEditingEat(null);
      setModalOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Xatolik yuz berdi.");
    } finally {
      setSubmitting(false);
    }
  };

  const checkModel = async (eat: Eat) => {
    setCheckingId(eat.id);
    try {
      await apiFetch(`/api/eat/check-model/${eat.id}/`);
      setError(null);
    } catch (err) {
      if (err instanceof AuthenticationError) return;
      setError(err instanceof ApiError ? err.message : "3D modelni tekshirishda xatolik yuz berdi.");
    } finally {
      await load();
      setCheckingId(null);
    }
  };

  const regenerateModel = async (eat: Eat) => {
    setCheckingId(eat.id);
    try {
      await apiFetch(`/api/eat/regenerate-model/${eat.id}/`, { method: "POST" });
      setError(null);
    } catch (err) {
      if (err instanceof AuthenticationError) return;
      setError(err instanceof ApiError ? err.message : "3D modelni qayta generatsiya qilishda xatolik yuz berdi.");
    } finally {
      await load();
      setCheckingId(null);
    }
  };

  const remove = async (eat: Eat) => {
    if (!confirm(`"${eat.name}" o'chirilsinmi?`)) return;
    await apiFetch(`/api/eat/${eat.id}/`, { method: "DELETE" });
    await load();
  };

  const openEdit = (eat: Eat) => {
    setEditingEat(eat);
    setName(eat.name);
    setDescription(eat.description);
    setPrice(eat.price);
    setCategoryId(eat.category ? String(eat.category) : "");
    setImage(null);
    setError(null);
    setModalOpen(true);
  };

  const closeModal = () => {
    if (submitting) return;
    setModalOpen(false);
    setEditingEat(null);
    resetForm();
  };

  if (restaurantLoading) return <p className="text-sm text-[var(--ink-muted)]">Yuklanmoqda...</p>;
  if (!current) return <p className="text-sm text-[var(--ink-muted)]">Avval restoran yarating.</p>;

  return (
    <div className="flex max-w-4xl flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-[var(--ink)]">Taomlar</h1>
        <Button
          onClick={() => {
            setError(null);
            setEditingEat(null);
            resetForm();
            setModalOpen(true);
          }}
        >
          <Plus size={16} strokeWidth={2} />
          Taom qo&apos;shish
        </Button>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50" onClick={closeModal}>
          <div className="absolute inset-0 bg-black/30" />
          <div
            className="animate-menu-drop absolute left-1/2 top-1/2 w-[min(680px,calc(100vw-2rem))] max-h-[85vh] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-3xl bg-[var(--surface)] p-5 shadow-lg sm:p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-bold text-[var(--ink)]">{editingEat ? "Taomni tahrirlash" : "Yangi taom"}</h2>
              <button
                onClick={closeModal}
                aria-label="Yopish"
                className="flex h-9 w-9 items-center justify-center rounded-xl text-[var(--ink)] ring-1 ring-[var(--line)]"
              >
                <X size={18} strokeWidth={2} />
              </button>
            </div>

            <form onSubmit={onSave} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-3">
                <Field label="Nomi">
                  <Input value={name} onChange={(e) => setName(e.target.value)} required />
                </Field>
                <Field label="Narxi (so'm)">
                  <Input type="number" value={price} onChange={(e) => setPrice(e.target.value)} required min={0} step="0.01" />
                </Field>
                <Field label="Kategoriya">
                  <select
                    value={categoryId}
                    onChange={(e) => setCategoryId(e.target.value)}
                    className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm"
                  >
                    <option value="">Kategoriyasiz</option>
                    {categories.filter((c) => c.is_active || c.id === editingEat?.category).map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}{!c.is_active ? " (yashirilgan)" : ""}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Rasm">
                  <Input type="file" accept="image/*" onChange={(e) => setImage(e.target.files?.[0] ?? null)} required={!editingEat} />
                </Field>
              </div>

              {/* Tavsif alohida, o'ng tomonda turadi */}
              <div className="flex flex-col">
                <Field label="Tavsif">
                  <Textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    required
                    minLength={5}
                    className="min-h-[9.5rem] flex-1 sm:min-h-full"
                  />
                </Field>
              </div>

              <div className="sm:col-span-2 flex flex-col gap-2">
                <ErrorText>{error}</ErrorText>
                <Button type="submit" disabled={submitting} className="self-start">
                  {submitting ? "Yuklanmoqda..." : editingEat ? "Saqlash" : "Qo'shish (3D generatsiya avtomatik boshlanadi)"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-sm text-[var(--ink-muted)]">Yuklanmoqda...</p>
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
          {eats.map((eat) => {
            const imageUrl = resolveMediaUrl(eat.image);
            return (
              <Card key={eat.id} className="flex flex-col gap-2 p-2">
                {eat.model_url ? (
                  <Model3DPreview modelUrl={resolveMediaUrl(eat.model_url)!} poster={imageUrl} alt={eat.name} />
                ) : (
                  imageUrl && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={imageUrl} alt={eat.name} className="aspect-square w-full rounded-lg object-cover" />
                  )
                )}
                <p className="text-sm font-semibold">{eat.name}</p>
                <p className="text-xs text-[var(--ink-muted)]">{formatPrice(eat.price)}</p>
                <p className="text-xs">
                  3D:{" "}
                  <span className={eat.model_url ? "text-green-600" : eat.model_error ? "text-red-600" : "text-amber-600"}>
                    {eat.model_url
                      ? "tayyor"
                      : eat.model_error
                        ? modelErrorLabel(eat)
                        : `${modelStatusLabel(eat.model_status)}${
                            typeof eat.model_progress === "number" ? ` ${Math.round(eat.model_progress)}%` : ""
                          }`}
                  </span>
                </p>
                {eat.usdz_status && (
                  <p className="text-xs">
                    iOS:{" "}
                    <span
                      className={
                        eat.usdz_status === "ready"
                          ? "text-green-600"
                          : eat.usdz_status === "failed"
                            ? "text-red-600"
                            : "text-amber-600"
                      }
                    >
                      {eat.usdz_status === "failed" ? usdzErrorLabel(eat) : USDZ_STATUS_LABELS[eat.usdz_status]}
                    </span>
                  </p>
                )}
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => openEdit(eat)}>
                    <Pencil size={15} /> Tahrirlash
                  </Button>
                  {!eat.model_url && (
                    <Button variant="secondary" onClick={() => checkModel(eat)} disabled={checkingId === eat.id}>
                      {checkingId === eat.id ? "..." : "Tekshirish"}
                    </Button>
                  )}
                  {eat.model_error && (
                    <Button variant="secondary" onClick={() => regenerateModel(eat)} disabled={checkingId === eat.id}>
                      Qayta generatsiya
                    </Button>
                  )}
                  <Button variant="danger" onClick={() => remove(eat)}>
                    O&apos;chirish
                  </Button>
                </div>
              </Card>
            );
          })}
          {eats.length === 0 && <p className="text-sm text-[var(--ink-muted)]">Hozircha taom yo&apos;q.</p>}
        </div>
      )}
    </div>
  );
}
