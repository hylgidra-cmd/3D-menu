import type { PublicMenu } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const SERVER_API_BASE_URL = process.env.INTERNAL_API_URL ?? API_BASE_URL;

export function resolveMediaUrl(path: string | null): string | null {
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${API_BASE_URL}${path}`;
}

export async function getPublicMenu(token: string): Promise<PublicMenu | null> {
  const res = await fetch(`${SERVER_API_BASE_URL}/api/public/menu/${token}/`, {
    cache: "no-store",
  });

  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Menu so'rovi muvaffaqiyatsiz: ${res.status}`);

  return res.json();
}
