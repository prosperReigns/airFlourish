import { useQuery } from "@tanstack/react-query";

import { listPaymentsRequest } from "@/lib/api/payments";
import { paymentsQueryKeys } from "@/lib/query-keys/payments";

export const usePaymentsQuery = () =>
  useQuery({
    queryKey: paymentsQueryKeys.list(),
    queryFn: () => listPaymentsRequest(),
  });
