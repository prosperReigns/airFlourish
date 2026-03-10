import { api } from "@/services/api";
import { useEffect, useState } from "react";
import { ActivityIndicator, FlatList, Text, View } from "react-native";

type Booking = {
  id: number;
  service_type: string;
  reference_code: string;
  total_price: string;
  currency: string;
  status: string;
};

export default function BookingsScreen() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchBookings = async () => {
    try {
      const response = await api.get("/bookings/");
      setBookings(response.data);
    } catch (err: any) {
      setError("Failed to load bookings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBookings();
  }, []);

  if (loading) {
    return (
      <View className="flex-1 items-center justify-center">
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (error) {
    return (
      <View className="flex-1 items-center justify-center">
        <Text className="text-red-500">{error}</Text>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-gray-50 p-5">
      <Text className="text-2xl font-bold mb-4">My Bookings</Text>

      {bookings.length === 0 ? (
        <View className="bg-white p-5 rounded-2xl shadow">
          <Text className="text-gray-500 text-center">
            You have no bookings yet.
          </Text>
        </View>
      ) : (
        <FlatList
          data={bookings}
          keyExtractor={(item) => item.id.toString()}
          renderItem={({ item }) => (
            <View className="bg-white p-4 rounded-2xl mb-4 shadow">
              <Text className="text-lg font-semibold capitalize">
                {item.service_type}
              </Text>

              <Text className="text-gray-600 mt-1">
                Ref: {item.reference_code}
              </Text>

              <Text className="text-gray-800 mt-2 font-semibold">
                {item.currency} {item.total_price}
              </Text>

              <View className="mt-2">
                <Text
                  className={`font-semibold ${
                    item.status === "confirmed"
                      ? "text-green-600"
                      : item.status === "cancelled"
                        ? "text-red-500"
                        : "text-yellow-600"
                  }`}
                >
                  {item.status}
                </Text>
              </View>
            </View>
          )}
        />
      )}
    </View>
  );
}
