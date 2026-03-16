import { listPayments, Payment } from "@/services/payment";
import { useEffect, useState } from "react";
import { ActivityIndicator, FlatList, Text, View } from "react-native";

export default function PaymentsScreen() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadPayments = async () => {
      try {
        const data = await listPayments();
        setPayments(data);
      } catch {
        setError("Unable to load payments.");
      } finally {
        setLoading(false);
      }
    };

    loadPayments();
  }, []);

  return (
    <View className="flex-1 bg-gray-50 p-5">
      <Text className="text-2xl font-bold mb-4">Payments</Text>

      {loading ? (
        <View className="items-center justify-center py-10">
          <ActivityIndicator size="large" />
        </View>
      ) : error ? (
        <View className="bg-white p-4 rounded-2xl shadow">
          <Text className="text-red-500 text-center">{error}</Text>
        </View>
      ) : payments.length === 0 ? (
        <View className="bg-white p-4 rounded-2xl shadow">
          <Text>No payments yet.</Text>
        </View>
      ) : (
        <FlatList
          data={payments}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <View className="bg-white p-4 rounded-2xl shadow mb-4">
              <Text className="text-gray-500 mb-1">
                Booking #{item.booking}
              </Text>
              <Text className="text-lg font-semibold">
                {item.currency} {item.amount}
              </Text>
              <Text className="text-gray-600 mt-1">
                Method: {item.payment_method}
              </Text>
              <Text
                className={`mt-1 font-semibold ${
                  item.status === "succeeded"
                    ? "text-green-600"
                    : item.status === "failed"
                      ? "text-red-500"
                      : "text-yellow-600"
                }`}
              >
                {item.status.toUpperCase()}
              </Text>
            </View>
          )}
        />
      )}
    </View>
  );
}
