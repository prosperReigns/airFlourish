export const hotelsQueryKeys = {
  all: ["hotels"] as const,
  search: (params: { city: string; checkIn: string; checkOut: string }) =>
    [...hotelsQueryKeys.all, "search", params] as const,
  detail: (hotelId: string) => [...hotelsQueryKeys.all, "detail", hotelId] as const,
};
