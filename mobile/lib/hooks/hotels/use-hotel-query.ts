import { useQuery } from "@tanstack/react-query";

import { getHotelRequest } from "@/lib/api/hotels";
import { hotelsQueryKeys } from "@/lib/query-keys/hotels";

export const useHotelQuery = (hotelId?: string) =>
  useQuery({
    queryKey: hotelsQueryKeys.detail(hotelId ?? "missing"),
    queryFn: () => getHotelRequest(hotelId as string),
    enabled: Boolean(hotelId),
  });
