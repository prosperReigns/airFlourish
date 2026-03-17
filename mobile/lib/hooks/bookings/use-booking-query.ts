import { useQuery } from "@tanstack/react-query";

import { getBookingRequest } from "@/lib/api/bookings";
import { bookingsQueryKeys } from "@/lib/query-keys/bookings";

export const useBookingQuery = (bookingId?: string) =>
  useQuery({
    queryKey: bookingsQueryKeys.detail(bookingId ?? "missing"),
    queryFn: () => getBookingRequest(bookingId as string),
    enabled: Boolean(bookingId),
  });
