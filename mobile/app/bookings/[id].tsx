import axios from "axios";
import { useSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ScrollView, Text, View } from "react-native";

interface BookingDetail {
  id: number;
  service_type: string;
  reference_code: string;
  status: string;
  total_price: number;
  currency: string;
  external_service_id?: string;
  details?: any;
}

export default function BookingDetailScreen() {
  const { id } = useSearchParams();
  const [booking, setBooking] = useState<BookingDetail | null>(null);

  useEffect(() => {
    axios
      .get(`https://192.168.0.200:8000/api/bookings/${id}/`)
      .then((res) => setBooking(res.data))
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
          {booking.currency} {booking.total_price}
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
