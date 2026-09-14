export function formatPrice(price: string): string {
  const value = Math.round(parseFloat(price));
  if (Number.isNaN(value)) return price;
  // Manual thousands-separator instead of toLocaleString("uz-UZ"): the server
  // (Node's ICU build) and the client browser can format the same number
  // differently, which breaks SSR hydration. This is deterministic everywhere.
  const withSeparators = value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${withSeparators} so'm`;
}
