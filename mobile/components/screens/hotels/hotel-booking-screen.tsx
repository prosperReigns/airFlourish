import { PressableOpacity } from "@/components/ui/pressable-opacity";
import { useBookHotelMutation } from "@/lib/hooks/hotels/use-book-hotel-mutation";
import { useHotelQuery } from "@/lib/hooks/hotels/use-hotel-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useMemo } from "react";
import { Text, View } from "react-native";

export default function HotelBookingScreen() {
  const { id, checkIn, checkOut, guests } = useLocalSearchParams();
  const router = useRouter();

  const hotelId = useMemo(() => (Array.isArray(id) ? id[0] : id), [id]);
  const guestCount = useMemo(() => Number(Array.isArray(guests) ? guests[0] : guests) || 1, [guests]);
  const checkInDate = useMemo(() => (Array.isArray(checkIn) ? checkIn[0] : checkIn) || "2026-03-01", [checkIn]);
  const checkOutDate = useMemo(() => (Array.isArray(checkOut) ? checkOut[0] : checkOut) || "2026-03-03", [checkOut]);

  const hotelQuery = useHotelQuery(hotelId as string | undefined);
  const bookHotelMutation = useBookHotelMutation();

  const hotel = hotelQuery.data;

  const bookHotel = async () => {
    if (!hotel) return;

    await bookHotelMutation.mutateAsync({
      hotelId: hotel.id,
      checkIn: checkInDate,
      checkOut: checkOutDate,
      guests: guestCount,
    });

    router.push("/bookings");
  };

  if (!hotel) return <Text className="text-center mt-10">Loading...</Text>;

  return (
    <View className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-4">{hotel.hotel_name}</Text>
      <Text className="text-gray-500 mb-2">{hotel.city}</Text>
      <Text className="text-gray-700 mb-1">{hotel.currency ?? "NGN"} {hotel.price_per_night ?? "0.00"}</Text>
      <PressableOpacity onPress={bookHotel} className="bg-blue-600 py-3 rounded-xl">
        <Text className="text-white text-center font-semibold">Book Now</Text>
      </PressableOpacity>
    </View>
  );
}
