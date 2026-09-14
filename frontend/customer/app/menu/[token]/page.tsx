import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getPublicMenu } from "@/lib/api";
import RestaurantHeader from "@/components/RestaurantHeader";
import MenuBrowser from "@/components/MenuBrowser";

type Params = { token: string };

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { token } = await params;
  const menu = await getPublicMenu(token);
  if (!menu) return { title: "Menyu topilmadi" };
  return { title: `${menu.restaurant.name} — Menyu` };
}

export default async function TableMenuPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { token } = await params;
  const menu = await getPublicMenu(token);

  if (!menu) notFound();

  return (
    <main
      className="flex min-h-screen flex-col"
      style={
        {
          "--brand": menu.restaurant.primary_color,
          "--brand-foreground": "#ffffff",
        } as React.CSSProperties
      }
    >
      <RestaurantHeader restaurant={menu.restaurant} table={menu.table} />
      <MenuBrowser categories={menu.categories} />
    </main>
  );
}
