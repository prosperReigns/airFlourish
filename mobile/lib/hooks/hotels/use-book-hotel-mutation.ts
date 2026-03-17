import { useMutation } from "@tanstack/react-query";

import { createHotelReservationRequest } from "@/lib/api/hotels";

export const useBookHotelMutation = () =>
  useMutation({
    mutationFn: createHotelReservationRequest,
  });
