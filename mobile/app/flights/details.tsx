import { api } from "@/services/api";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Text, TouchableOpacity, View } from "react-native";

export default function FlightDetailsScreen() {
  const router = useRouter();
  const { flight } = useLocalSearchParams();

  const parsedFlight = JSON.parse(flight as string);

  const handleBook = async () => {
    await api.post("/flights/book/", {
      flight: parsedFlight,
    });

    router.push("/(tabs)/bookings");
  };

  return (
    <View className="flex-1 bg-gray-50 p-6">
      <Text className="text-2xl font-bold mb-4">Flight Details</Text>

      <Text className="text-lg">
        Price: {parsedFlight.price.total} {parsedFlight.price.currency}
      </Text>

      <Text className="mt-2 text-gray-600">
        Airline: {parsedFlight.validatingAirlineCodes[0]}
      </Text>

      <TouchableOpacity
        onPress={handleBook}
        className="mt-6 bg-blue-600 py-4 rounded-2xl items-center"
      >
        <Text className="text-white font-semibold text-lg">Book Flight</Text>
      </TouchableOpacity>
    </View>
  );
}
