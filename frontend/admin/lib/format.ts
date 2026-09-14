export function formatPrice(price: string): string {
  const value = Math.round(parseFloat(price));
  if (Number.isNaN(value)) return price;
  // Manual thousands-separator instead of toLocaleString("uz-UZ"): its output
  // can vary between Node's ICU build and the browser's, so keep it deterministic.
  const withSeparators = value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${withSeparators} so'm`;
}
