/** Browser requests remain same-origin; SSR can use a private service URL. */
export const API_BASE = typeof window !== "undefined"
  ? "/api"
  : process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "/api";
