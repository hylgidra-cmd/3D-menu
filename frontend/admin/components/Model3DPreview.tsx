"use client";

import "@google/model-viewer";

export default function Model3DPreview({
  modelUrl,
  poster,
  alt,
}: {
  modelUrl: string;
  poster?: string | null;
  alt: string;
}) {
  return (
    <model-viewer
      src={modelUrl}
      poster={poster ?? undefined}
      alt={alt}
      camera-controls
      auto-rotate
      environment-image="neutral"
      exposure="1"
      shadow-intensity="1"
      loading="eager"
      reveal="auto"
      className="aspect-square w-full rounded-lg bg-[var(--line)]"
    />
  );
}
