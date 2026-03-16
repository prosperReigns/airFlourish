import { api } from "@/services/api";
import { useRouter, useSearchParams } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { Text, TouchableOpacity, View } from "react-native";

interface HotelDetail {
  id: number;
  hotel_name: string;
  price_per_night?: number;
  currency?: string;
  city: string;
  address?: string;
}

export default function HotelBookingScreen() {
  const { id, checkIn, checkOut, guests } = useSearchParams();
  const router = useRouter();
  const [hotel, setHotel] = useState<HotelDetail | null>(null);
  const hotelId = useMemo(
    () => (Array.isArray(id) ? id[0] : id),
    [id],
  );
  const guestCount = useMemo(
    () => Number(Array.isArray(guests) ? guests[0] : guests) || 1,
    [guests],
  );
  const checkInDate = useMemo(
    () => (Array.isArray(checkIn) ? checkIn[0] : checkIn) || "2026-03-01",
    [checkIn],
  );
  const checkOutDate = useMemo(
    () => (Array.isArray(checkOut) ? checkOut[0] : checkOut) || "2026-03-03",
    [checkOut],
  );

  useEffect(() => {
    if (!hotelId) return;
    api
      .get(`hotels/hotels/${hotelId}/`)
      .then((res) => setHotel(res.data))
      .catch((err) => console.log(err));
  }, [hotelId]);

  const bookHotel = () => {
    if (!hotel) return;
    api
      .post("hotels/hotel-reservations/", {
        hotel_id: hotel.id,
        check_in: checkInDate,
        check_out: checkOutDate,
        guests: guestCount,
      })
      .then((res) => router.push("/bookings"))
      .catch((err) => console.log(err));
  };

  if (!hotel) return <Text className="text-center mt-10">Loading...</Text>;

  return (
    <View className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-4">{hotel.hotel_name}</Text>
      <Text className="text-gray-500 mb-2">{hotel.city}</Text>
      <Text className="text-gray-700 mb-1">
        {hotel.currency ?? "NGN"} {hotel.price_per_night ?? "0.00"}
      </Text>
      <Text className="text-gray-500 mb-4">
        {checkInDate} → {checkOutDate} · {guestCount} guest
        {guestCount > 1 ? "s" : ""}
      </Text>

      <TouchableOpacity
        onPress={bookHotel}
        className="bg-blue-600 py-3 rounded-xl"
      >
        <Text className="text-white text-center font-semibold">Book Now</Text>
      </TouchableOpacity>
    </View>
  );
}
