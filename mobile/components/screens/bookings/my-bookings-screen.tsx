import { RefreshControl, ScrollView, Text, View } from "react-native";

import { PressableOpacity } from "@/components/ui/pressable-opacity";
import { useBookingsQuery } from "@/lib/hooks/bookings/use-bookings-query";
import { useRouter } from "expo-router";

export default function MyBookingsScreen() {
  const router = useRouter();
  const { data: bookings = [], isLoading, refetch, isRefetching } = useBookingsQuery();

  if (isLoading) return <Text className="text-center mt-10">Loading...</Text>;

  return (
    <ScrollView
      className="bg-gray-50 flex-1 px-4 pt-4"
      refreshControl={
        <RefreshControl refreshing={isRefetching} onRefresh={() => void refetch()} />
      }
    >
      <Text className="text-2xl font-bold mb-4">My Bookings</Text>

      {bookings.length === 0 && <Text className="text-center mt-10 text-gray-500">No bookings yet.</Text>}

      {bookings.map((booking) => (
        <View key={booking.id} className="bg-white p-4 rounded-2xl shadow mb-4">
          <Text className="text-lg font-semibold mb-2">{booking.service_type}</Text>
          <Text className="text-gray-700 mb-2">{booking.reference_code}</Text>
          <Text className="text-gray-700 mb-2">
            {booking.currency ?? "NGN"} {booking.total_price ?? "0.00"}
          </Text>

          {booking.status === "pending" && (
            <PressableOpacity
              className="bg-blue-600 py-2 rounded-xl mt-2"
              onPress={() => router.push(`/payments?bookingId=${booking.id}`)}
            >
              <Text className="text-white text-center font-semibold">Pay Now</Text>
            </PressableOpacity>
          )}
        </View>
      ))}
    </ScrollView>
  );
}
