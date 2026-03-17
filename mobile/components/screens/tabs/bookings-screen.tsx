import { ActivityIndicator, FlatList, Text, View } from "react-native";

import type { Booking } from "@/lib/api/bookings";
import { useBookingsQuery } from "@/lib/hooks/bookings/use-bookings-query";

export default function TabBookingsScreen() {
  const { data: bookings = [], isLoading, error } = useBookingsQuery();

  if (isLoading) {
    return (
      <View className="flex-1 items-center justify-center">
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (error) {
    return (
      <View className="flex-1 items-center justify-center">
        <Text className="text-red-500">Failed to load bookings</Text>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-gray-50 p-5">
      <Text className="text-2xl font-bold mb-4">My Bookings</Text>
      {bookings.length === 0 ? (
        <View className="bg-white p-5 rounded-2xl shadow">
          <Text className="text-gray-500 text-center">You have no bookings yet.</Text>
        </View>
      ) : (
        <FlatList
          data={bookings}
          keyExtractor={(item) => item.id.toString()}
          renderItem={({ item }: { item: Booking }) => (
            <View className="bg-white p-4 rounded-2xl mb-4 shadow">
              <Text className="text-lg font-semibold capitalize">{item.service_type}</Text>
              <Text className="text-gray-600 mt-1">Ref: {item.reference_code}</Text>
              <Text className="text-gray-800 mt-2 font-semibold">
                {item.currency ?? "NGN"} {item.total_price ?? "0.00"}
              </Text>
            </View>
          )}
        />
      )}
    </View>
  );
}
