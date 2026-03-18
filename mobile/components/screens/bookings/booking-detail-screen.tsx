import { useLocalSearchParams } from "expo-router";
import { ScrollView, Text, View } from "react-native";

import { useBookingQuery } from "@/lib/hooks/bookings/use-booking-query";

export function BookingDetailScreen() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const { data: booking } = useBookingQuery(id);

  if (!booking) return <Text className="text-center mt-10">Loading...</Text>;

  return (
    <ScrollView className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-4">{booking.service_type.toUpperCase()} Booking</Text>

      <View className="bg-white rounded-2xl p-4 shadow mb-4">
        <Text className="text-gray-500 mb-1">Reference Code</Text>
        <Text className="text-lg font-semibold mb-2">{booking.reference_code}</Text>
        <Text className="text-gray-500 mb-1">Status</Text>
        <Text
          className={`font-medium mb-2 ${booking.status === "confirmed" ? "text-green-600" : "text-yellow-600"}`}
        >
          {booking.status.toUpperCase()}
        </Text>
        <Text className="text-gray-500 mb-1">Total Price</Text>
        <Text className="text-gray-700 mb-2">
          {booking.currency ?? "NGN"} {booking.total_price ?? "0.00"}
        </Text>
      </View>
    </ScrollView>
  );
}
