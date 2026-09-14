import Image from "next/image";
import { resolveMediaUrl } from "@/lib/api";
import type { PublicRestaurant, PublicTable } from "@/lib/types";

export default function RestaurantHeader({
  restaurant,
  table,
}: {
  restaurant: PublicRestaurant;
  table: PublicTable;
}) {
  const cover = resolveMediaUrl(restaurant.cover_image);
  const logo = resolveMediaUrl(restaurant.logo);

  return (
    <header className="relative">
      <div className="relative h-48 w-full overflow-hidden bg-[var(--brand)] sm:h-56">
        {cover && (
          <Image src={cover} alt="" fill unoptimized priority className="object-cover" />
        )}
        <div
          className="absolute inset-0"
          style={{
            background: cover
              ? "linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0) 35%, var(--bg) 100%)"
              : "linear-gradient(180deg, transparent 0%, var(--bg) 100%)",
          }}
        />
      </div>

      <div className="relative -mt-9 flex flex-col items-center px-6 text-center">
        <div className="flex h-[72px] w-[72px] items-center justify-center overflow-hidden rounded-full bg-[var(--surface)] shadow-sm ring-4 ring-[var(--bg)]">
          {logo ? (
            <Image src={logo} alt={restaurant.name} width={72} height={72} unoptimized className="h-full w-full object-cover" />
          ) : (
            <span className="font-[family-name:var(--font-display)] text-2xl italic text-[var(--brand)]">
              {restaurant.name.slice(0, 1).toUpperCase()}
            </span>
          )}
        </div>

        <h1 className="mt-3 font-[family-name:var(--font-display)] text-2xl font-medium tracking-tight text-[var(--ink)]">
          {restaurant.name}
        </h1>

        <p className="mt-1 text-[13px] tracking-wide text-[var(--ink-muted)] uppercase">
          Stol {table.name}{table.place ? ` · ${table.place}` : ""}
        </p>

        {restaurant.description && (
          <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-[var(--ink-muted)]">
            {restaurant.description}
          </p>
        )}
      </div>
    </header>
  );
}
