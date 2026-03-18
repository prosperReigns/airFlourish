import { useRouter } from "expo-router";
import { FlatList, Text, View } from "react-native";

import type { Booking } from "@/lib/api/bookings";
import { useBookingsQuery } from "@/lib/hooks/bookings/use-bookings-query";
import { PressableOpacity } from "@/components/ui/pressable-opacity";

export function BookingsScreen() {
  const router = useRouter();
  const { data: bookings = [] } = useBookingsQuery();

  const renderBooking = ({ item }: { item: Booking }) => (
    <PressableOpacity
      onPress={() => router.push(`/bookings/${item.id}`)}
      className="bg-white rounded-2xl p-4 mb-4 shadow"
    >
      <Text className="text-lg font-semibold mb-1">{item.service_type.toUpperCase()} Booking</Text>
      <Text className="text-gray-500 mb-1">Ref: {item.reference_code}</Text>
      <Text
        className={`font-medium ${item.status === "confirmed" ? "text-green-600" : "text-yellow-600"}`}
      >
        {item.status.toUpperCase()}
      </Text>
      <Text className="text-gray-700 mt-1">
        {item.currency ?? "NGN"} {item.total_price ?? "0.00"}
      </Text>
    </PressableOpacity>
  );

  return (
    <View className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-6">My Bookings</Text>
      <FlatList
        data={bookings}
        keyExtractor={(item) => item.id.toString()}
        renderItem={renderBooking}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}
