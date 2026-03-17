import { useMutation } from "@tanstack/react-query";

import { registerRequest } from "@/lib/api/auth";

export const useRegisterMutation = () =>
  useMutation({
    mutationFn: registerRequest,
  });
