import { useQuery } from "@tanstack/react-query";

import { searchFlightsRequest } from "@/lib/api/flights";
import { flightsQueryKeys } from "@/lib/query-keys/flights";

export const useFlightsSearchQuery = (params: {
  origin?: string;
  destination?: string;
  departureDate?: string;
  returnDate?: string;
}) =>
  useQuery({
    queryKey: flightsQueryKeys.search({
      origin: params.origin ?? "",
      destination: params.destination ?? "",
      departureDate: params.departureDate ?? "",
      returnDate: params.returnDate,
    }),
    queryFn: () =>
      searchFlightsRequest({
        origin: params.origin as string,
        destination: params.destination as string,
        departureDate: params.departureDate as string,
        returnDate: params.returnDate,
      }),
    enabled: Boolean(params.origin && params.destination && params.departureDate),
  });
