export const flightsQueryKeys = {
  all: ["flights"] as const,
  search: (params: {
    origin: string;
    destination: string;
    departureDate: string;
    returnDate?: string;
  }) => [...flightsQueryKeys.all, "search", params] as const,
};
