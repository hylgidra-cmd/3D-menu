"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import FoodCard from "./FoodCard";
import type { PublicCategory, PublicEat } from "@/lib/types";

// model-viewer touches browser globals at module load time, so it must
// never be evaluated during SSR.
const FoodDetailModal = dynamic(() => import("./FoodDetailModal"), { ssr: false });

export default function MenuBrowser({ categories }: { categories: PublicCategory[] }) {
  const visibleCategories = categories.filter((c) => c.eats.length > 0);
  const [activeId, setActiveId] = useState(visibleCategories[0]?.id ?? null);
  const [selectedEat, setSelectedEat] = useState<PublicEat | null>(null);

  if (visibleCategories.length === 0) {
    return (
      <p className="px-6 py-16 text-center text-sm text-[var(--ink-muted)]">
        Hozircha menyu bo&apos;sh.
      </p>
    );
  }

  const active = visibleCategories.find((c) => c.id === activeId) ?? visibleCategories[0];

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col">
      <nav className="sticky top-0 z-10 flex gap-6 overflow-x-auto bg-[var(--bg)]/95 px-6 pt-6 pb-0 backdrop-blur">
        {visibleCategories.map((c) => (
          <button
            key={c.id}
            onClick={() => setActiveId(c.id)}
            className={`shrink-0 whitespace-nowrap border-b-2 pb-3 text-[15px] font-medium transition ${
              c.id === active.id
                ? "border-[var(--brand)] text-[var(--ink)]"
                : "border-transparent text-[var(--ink-muted)]"
            }`}
          >
            {c.name}
          </button>
        ))}
      </nav>
      <div className="h-px w-full bg-[var(--line)]" />

      <div key={active.id} className="animate-fade-in grid grid-cols-2 gap-x-3 gap-y-6 px-6 py-6 sm:grid-cols-3">
        {active.eats.map((eat) => (
          <FoodCard key={eat.id} eat={eat} onSelect={() => setSelectedEat(eat)} />
        ))}
      </div>

      {selectedEat && (
        <FoodDetailModal eat={selectedEat} onClose={() => setSelectedEat(null)} />
      )}
    </div>
  );
}
