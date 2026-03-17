import { apiClient } from "@/lib/api/client";

export type Hotel = {
  id: number;
  hotel_name: string;
  price_per_night?: number;
  currency?: string;
  city: string;
};

export type HotelDetail = Hotel & {
  address?: string;
};

export const listHotelsRequest = async (params: {
  city: string;
  checkIn: string;
  checkOut: string;
}) => {
  const response = await apiClient.get<Hotel[]>("hotels/hotels/", {
    params: {
      city: params.city,
      check_in: params.checkIn,
      check_out: params.checkOut,
      guests: 1,
    },
  });

  return response.data;
};

export const getHotelRequest = async (hotelId: string) => {
  const response = await apiClient.get<HotelDetail>(`hotels/hotels/${hotelId}/`);
  return response.data;
};

export const createHotelReservationRequest = async (payload: {
  hotelId: number;
  checkIn: string;
  checkOut: string;
  guests: number;
}) => {
  const response = await apiClient.post("hotels/hotel-reservations/", {
    hotel_id: payload.hotelId,
    check_in: payload.checkIn,
    check_out: payload.checkOut,
    guests: payload.guests,
  });

  return response.data;
};
