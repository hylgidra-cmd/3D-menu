import Image from "next/image";
import { resolveMediaUrl } from "@/lib/api";
import { formatPrice } from "@/lib/format";
import type { PublicEat } from "@/lib/types";

export default function FoodCard({
  eat,
  onSelect,
}: {
  eat: PublicEat;
  onSelect: () => void;
}) {
  const hasAr = Boolean(eat.model_url);
  const imageUrl = resolveMediaUrl(eat.image);

  return (
    <button
      onClick={onSelect}
      className="group flex flex-col overflow-hidden rounded-[20px] bg-[var(--surface)] text-left transition active:scale-[0.98]"
    >
      <div className="relative aspect-[4/3] w-full overflow-hidden rounded-[20px] bg-[var(--line)]">
        {imageUrl && (
          <Image
            src={imageUrl}
            alt={eat.name}
            fill
            unoptimized
            className="object-cover transition duration-500 group-hover:scale-[1.04]"
          />
        )}
        {hasAr && (
          <span className="absolute left-2.5 top-2.5 flex items-center gap-1 rounded-full bg-white/90 px-2 py-1 text-[10px] font-semibold tracking-wide text-[var(--ink)] backdrop-blur-sm">
            <svg viewBox="0 0 24 24" className="h-3 w-3" fill="currentColor">
              <path d="M12 2 3 7v10l9 5 9-5V7l-9-5Zm0 2.3 6.5 3.6L12 11.5 5.5 7.9 12 4.3ZM5 9.2l6 3.3v7L5 16.2V9.2Zm8 10.3v-7l6-3.3v7l-6 3.3Z" />
            </svg>
            AR
          </span>
        )}
      </div>
      <div className="flex flex-col gap-0.5 px-1 pt-2.5">
        <h3 className="text-[15px] font-medium leading-snug text-[var(--ink)]">{eat.name}</h3>
        <p className="line-clamp-1 text-[13px] text-[var(--ink-muted)]">{eat.description}</p>
        <p className="mt-1 text-[13px] font-semibold text-[var(--ink)]">
          {formatPrice(eat.price)}
        </p>
      </div>
    </button>
  );
}
