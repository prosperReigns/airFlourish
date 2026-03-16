import { api } from "./api";

export type Booking = {
  id: number;
  service_type: string;
  reference_code: string;
  status: string;
  total_price?: number | string | null;
  currency?: string;
  created_at?: string;
  external_service_id?: string | null;
  details?: unknown;
};

const BOOKINGS_PATH = "bookings/bookings/";

export const listBookings = async () => {
  const response = await api.get<Booking[]>(BOOKINGS_PATH);
  return response.data;
};

export const getBooking = async (bookingId: number | string) => {
  const response = await api.get<Booking>(`${BOOKINGS_PATH}${bookingId}/`);
  return response.data;
};
