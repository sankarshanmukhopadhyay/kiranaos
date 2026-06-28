export const SIDEBAR_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  customers: "Customers",
  udhaari: "Udhaari",
  analytics: "Analytics",
  simulate: "Simulate WA",
};

export const SIDEBAR_ICONS: Record<string, JSX.Element> = {
  dashboard: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
      <path d="M2 2h5v5H2V2zm7 0h5v5H9V2zM2 9h5v5H2V9zm7 0h5v5H9V9z" />
    </svg>
  ),
  customers: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
      <path d="M8 8a3 3 0 100-6 3 3 0 000 6zm-5 6a5 5 0 1110 0H3z" />
    </svg>
  ),
  udhaari: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
      <path d="M8 1a2 2 0 012 2v2H6V3a2 2 0 012-2zm3 4V3a3 3 0 10-6 0v2H3.5A1.5 1.5 0 002 6.5v7A1.5 1.5 0 003.5 15h9a1.5 1.5 0 001.5-1.5v-7A1.5 1.5 0 0012.5 5H11z" />
    </svg>
  ),
  analytics: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
      <path
        d="M1 13V11l4-4 4 3 5-7"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  ),
  simulate: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51a7 7 0 01-1.24 9.884 9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374A9.86 9.86 0 012.157 11.892C2.16 5.335 7.495 0 12.05 0c2.64 0 5.122 1.03 6.988 2.898A9.825 9.825 0 0121.93 9.89c-.003 5.45-4.437 9.885-9.885 9.885" />
    </svg>
  ),
};
