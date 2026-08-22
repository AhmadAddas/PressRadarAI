export const publicApiUrl =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const internalApiUrl = process.env.API_INTERNAL_URL ?? publicApiUrl;
