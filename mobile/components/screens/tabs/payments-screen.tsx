import { ActivityIndicator, FlatList, Text, View } from "react-native";

import type { Payment } from "@/lib/api/payments";
import { usePaymentsQuery } from "@/lib/hooks/payments/use-payments-query";

export default function TabPaymentsScreen() {
  const { data: payments = [], isLoading, error } = usePaymentsQuery();

  return (
    <View className="flex-1 bg-gray-50 p-5">
      <Text className="text-2xl font-bold mb-4">Payments</Text>

      {isLoading ? (
        <View className="items-center justify-center py-10">
          <ActivityIndicator size="large" />
        </View>
      ) : error ? (
        <View className="bg-white p-4 rounded-2xl shadow">
          <Text className="text-red-500 text-center">Unable to load payments.</Text>
        </View>
      ) : payments.length === 0 ? (
        <View className="bg-white p-4 rounded-2xl shadow">
          <Text>No payments yet.</Text>
        </View>
      ) : (
        <FlatList
          data={payments}
          keyExtractor={(item) => item.id}
          renderItem={({ item }: { item: Payment }) => (
            <View className="bg-white p-4 rounded-2xl shadow mb-4">
              <Text className="text-gray-500 mb-1">Booking #{item.booking}</Text>
              <Text className="text-lg font-semibold">{item.currency} {item.amount}</Text>
              <Text className="text-gray-600 mt-1">Method: {item.payment_method}</Text>
            </View>
          )}
        />
      )}
    </View>
  );
}
