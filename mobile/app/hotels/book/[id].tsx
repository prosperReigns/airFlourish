import axios from "axios";
import { useRouter, useSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { Text, TouchableOpacity, View } from "react-native";

interface HotelDetail {
  hotel_id: string;
  hotel_name: string;
  price: number;
  city: string;
}

export default function HotelBookingScreen() {
  const { id } = useSearchParams();
  const router = useRouter();
  const [hotel, setHotel] = useState<HotelDetail | null>(null);

  useEffect(() => {
    axios
      .get(`https://127.0.0.1:8000/api/hotels/detail/`, {
        params: { hotel_id: id },
      })
      .then((res) => setHotel(res.data))
      .catch((err) => console.log(err));
  }, [id]);

  const bookHotel = () => {
    axios
      .post(`https://127.0.0.1:8000/api/hotels/reservations/`, {
        hotel_id: hotel?.hotel_id,
        hotel_name: hotel?.hotel_name,
        total_price: hotel?.price,
        arrival_date: "2026-03-01",
        departure_date: "2026-03-03",
        guests: 1,
        rooms: 1,
      })
      .then((res) => router.push("/bookings"))
      .catch((err) => console.log(err));
  };

  if (!hotel) return <Text className="text-center mt-10">Loading...</Text>;

  return (
    <View className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-4">{hotel.hotel_name}</Text>
      <Text className="text-gray-500 mb-2">{hotel.city}</Text>
      <Text className="text-gray-700 mb-4">NGN {hotel.price}</Text>

      <TouchableOpacity
        onPress={bookHotel}
        className="bg-blue-600 py-3 rounded-xl"
      >
        <Text className="text-white text-center font-semibold">Book Now</Text>
      </TouchableOpacity>
    </View>
  );
}
