import { useMutation } from "@tanstack/react-query";

import { secureBookFlightRequest } from "@/lib/api/flights";

export const useSecureFlightBookingMutation = () =>
  useMutation({
    mutationFn: secureBookFlightRequest,
  });
