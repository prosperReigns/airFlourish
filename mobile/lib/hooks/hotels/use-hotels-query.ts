import { useQuery } from "@tanstack/react-query";

import { listHotelsRequest } from "@/lib/api/hotels";
import { hotelsQueryKeys } from "@/lib/query-keys/hotels";

export const useHotelsQuery = (params: {
  city: string;
  checkIn: string;
  checkOut: string;
}) =>
  useQuery({
    queryKey: hotelsQueryKeys.search(params),
    queryFn: () => listHotelsRequest(params),
    enabled: false,
  });
