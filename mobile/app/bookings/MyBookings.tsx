import { View, Text, ScrollView, TouchableOpacity, RefreshControl } from "react-native";
import { useState, useEffect } from "react";
import axios from "axios";
import { useRouter } from "expo-router";

interface Booking {
  id: number;
  service_type: string;
  total_price: number;
  currency: string;
  status: string;
  reference_code: string;
}

export default function MyBookings() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();

  const fetchBookings = async () => {
    try {
      const res = await axios.get("https://your-backend.com/api/bookings/");
      setBookings(res.data);
    } catch (err) {
      console.log(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchBookings();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchBookings();
  };

  if (loading) return <Text className="text-center mt-10">Loading...</Text>;

  return (
    <ScrollView
      className="bg-gray-50 flex-1 px-4 pt-4"
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <Text className="text-2xl font-bold mb-4">My Bookings</Text>

      {bookings.length === 0 && <Text className="text-center mt-10 text-gray-500">No bookings yet.</Text>}

      {bookings.map((booking) => (
        <View
          key={booking.id}
          className="bg-white p-4 rounded-2xl shadow mb-4"
        >
          <Text className="text-gray-500 mb-1">Service</Text>
          <Text className="text-lg font-semibold mb-2">{booking.service_type}</Text>

          <Text className="text-gray-500 mb-1">Reference</Text>
          <Text className="text-gray-700 mb-2">{booking.reference_code}</Text>

          <Text className="text-gray-500 mb-1">Amount</Text>
          <Text className="text-gray-700 mb-2">
            {booking.currency} {booking.total_price}
          </Text>

          <Text className="text-gray-500 mb-1">Status</Text>
          <Text
            className={`font-semibold mb-2 ${
              booking.status === "pending"
                ? "text-yellow-500"
                : booking.status === "confirmed"
                ? "text-green-500"
                : booking.status === "cancelled" || booking.status === "failed"
                ? "text-red-500"
                : "text-gray-500"
            }`}
          >
            {booking.status.toUpperCase()}
          </Text>

          {booking.status === "pending" && (
            <TouchableOpacity
              className="bg-blue-600 py-2 rounded-xl mt-2"
              onPress={() => router.push(`/payments?bookingId=${booking.id}`)}
            >
              <Text className="text-white text-center font-semibold">Pay Now</Text>
            </TouchableOpacity>
          )}
        </View>
      ))}
    </ScrollView>
  );
}