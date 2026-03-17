import { useQuery } from "@tanstack/react-query";

import { listBookingsRequest } from "@/lib/api/bookings";
import { bookingsQueryKeys } from "@/lib/query-keys/bookings";

export const useBookingsQuery = () =>
  useQuery({
    queryKey: bookingsQueryKeys.list(),
    queryFn: listBookingsRequest,
  });
