import { useQuery } from "@tanstack/react-query";

import { listTransportOptionsRequest } from "@/lib/api/transport";
import { transportQueryKeys } from "@/lib/query-keys/transport";

export const useTransportOptionsQuery = () =>
  useQuery({
    queryKey: transportQueryKeys.options(),
    queryFn: listTransportOptionsRequest,
  });
