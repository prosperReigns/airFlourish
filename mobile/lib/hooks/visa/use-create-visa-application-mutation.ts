import { useMutation } from "@tanstack/react-query";

import { createVisaApplicationRequest } from "@/lib/api/visa";

export const useCreateVisaApplicationMutation = () =>
  useMutation({
    mutationFn: createVisaApplicationRequest,
  });
