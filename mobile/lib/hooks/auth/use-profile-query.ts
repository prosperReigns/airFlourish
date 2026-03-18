import { useQuery } from "@tanstack/react-query";

import { fetchProfileRequest } from "@/lib/api/auth";
import { authQueryKeys } from "@/lib/query-keys/auth";

export const useProfileQuery = () =>
  useQuery({
    queryKey: authQueryKeys.profile(),
    queryFn: fetchProfileRequest,
  });
