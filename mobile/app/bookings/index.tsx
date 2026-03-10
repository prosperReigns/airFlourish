import axios from "axios";
import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { FlatList, Text, TouchableOpacity, View } from "react-native";

interface Booking {
  id: number;
  service_type: string;
  reference_code: string;
  status: string;
  total_price: number;
  currency: string;
  external_service_id?: string;
}

export default function MyBookingsScreen() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const router = useRouter();

  useEffect(() => {
    // Fetch user bookings from backend
    axios
      .get("https://192.168.0.200:8000/api/bookings/")
      .then((res) => setBookings(res.data))
      .catch((err) => console.log(err));
  }, []);

  const renderBooking = ({ item }: { item: Booking }) => (
    <TouchableOpacity
      onPress={() => router.push(`/bookings/${item.id}`)}
      className="bg-white rounded-2xl p-4 mb-4 shadow"
    >
      <Text className="text-lg font-semibold mb-1">
        {item.service_type.toUpperCase()} Booking
      </Text>
      <Text className="text-gray-500 mb-1">Ref: {item.reference_code}</Text>
      <Text
        className={`font-medium ${item.status === "confirmed" ? "text-green-600" : "text-yellow-600"}`}
      >
        {item.status.toUpperCase()}
      </Text>
      <Text className="text-gray-700 mt-1">
        {item.currency} {item.total_price}
      </Text>
    </TouchableOpacity>
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
