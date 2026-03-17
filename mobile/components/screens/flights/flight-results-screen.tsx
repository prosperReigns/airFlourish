import { PressableOpacity } from "@/components/ui/pressable-opacity";
import { useFlightsSearchQuery } from "@/lib/hooks/flights/use-flights-search-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { ActivityIndicator, FlatList, Text, View } from "react-native";

export default function FlightResultsScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    origin?: string;
    destination?: string;
    departureDate?: string;
    returnDate?: string;
  }>();

  const { data: flights = [], isLoading } = useFlightsSearchQuery({
    origin: params.origin,
    destination: params.destination,
    departureDate: params.departureDate,
    returnDate: params.returnDate,
  });

  if (isLoading) {
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
        keyExtractor={(item, index) => item?.id ?? `${index}`}
        renderItem={({ item }) => (
          <PressableOpacity
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
          </PressableOpacity>
        )}
      />
    </View>
  );
}
