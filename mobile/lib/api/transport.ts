import { apiClient } from "@/lib/api/client";

export type TransportOption = {
  id: number;
  transport_name: string;
  pickup_location: string;
  dropoff_location: string;
  price_per_passenger: number;
  currency: string;
  passengers: number;
};

export const listTransportOptionsRequest = async () => {
  const response = await apiClient.get<TransportOption[]>(
    "transport/transport-options/",
  );

  return response.data;
};
