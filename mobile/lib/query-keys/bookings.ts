export const bookingsQueryKeys = {
  all: ["bookings"] as const,
  list: () => [...bookingsQueryKeys.all, "list"] as const,
  detail: (id: string | number) => [...bookingsQueryKeys.all, "detail", id] as const,
};
