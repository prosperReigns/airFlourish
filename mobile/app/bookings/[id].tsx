import { Booking, getBooking } from "@/services/booking";
import { useSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ScrollView, Text, View } from "react-native";

export default function BookingDetailScreen() {
  const { id } = useSearchParams();
  const [booking, setBooking] = useState<Booking | null>(null);

  useEffect(() => {
    if (!id) return;
    getBooking(id as string)
      .then((data) => setBooking(data))
      .catch((err) => console.log(err));
  }, [id]);

  if (!booking) return <Text className="text-center mt-10">Loading...</Text>;

  return (
    <ScrollView className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-4">
        {booking.service_type.toUpperCase()} Booking
      </Text>

      <View className="bg-white rounded-2xl p-4 shadow mb-4">
        <Text className="text-gray-500 mb-1">Reference Code</Text>
        <Text className="text-lg font-semibold mb-2">
          {booking.reference_code}
        </Text>

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

        {/* Optional: Show service-specific details */}
        {booking.details && (
          <View className="mt-2">
            <Text className="text-gray-500 mb-1">Details</Text>
            <Text className="text-gray-700">
              {JSON.stringify(booking.details, null, 2)}
            </Text>
          </View>
        )}
      </View>
    </ScrollView>
  );
}
