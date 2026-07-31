export function formatCurrency(value: string): string {
  return `$${Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString();
}
