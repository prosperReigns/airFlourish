import { api } from "@/services/api";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import {
    ActivityIndicator,
    FlatList,
    Text,
    TouchableOpacity,
    View,
} from "react-native";

export default function FlightResultsScreen() {
  const router = useRouter();
  const { origin, destination, departureDate, returnDate } =
    useLocalSearchParams();

  const [flights, setFlights] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchFlights = useCallback(async () => {
    try {
      const response = await api.get("bookings/flights/search/", {
        params: {
          origin,
          destination,
          departure_date: departureDate,
          return_date: returnDate,
        },
      });

      setFlights(response.data);
    } catch (error) {
      console.log(error);
    } finally {
      setLoading(false);
    }
  }, [departureDate, destination, origin, returnDate]);

  useEffect(() => {
    fetchFlights();
  }, [fetchFlights]);

  if (loading) {
    return (
      <View className="flex-1 items-center justify-center">
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-gray-50 p-4">
      <Text className="text-xl font-bold mb-4">Available Flights</Text>

      <FlatList
        data={flights}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <TouchableOpacity
            onPress={() =>
              router.push({
                pathname: "/flights/details",
                params: { flight: JSON.stringify(item) },
              })
            }
            className="bg-white p-4 rounded-2xl mb-4 shadow"
          >
            <Text className="font-semibold text-lg">
              {item.itineraries[0].segments[0].departure.iataCode} →
              {item.itineraries[0].segments[0].arrival.iataCode}
            </Text>

            <Text className="text-gray-500 mt-1">
              {item.price.total} {item.price.currency}
            </Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}
