import { useMutation } from "@tanstack/react-query";

import { initiateCardPaymentRequest } from "@/lib/api/payments";

export const useInitiateCardPaymentMutation = () =>
  useMutation({
    mutationFn: initiateCardPaymentRequest,
  });
