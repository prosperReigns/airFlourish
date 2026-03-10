import { useRouter } from "expo-router";
import { useState } from "react";
import { Text, TextInput, TouchableOpacity, View } from "react-native";

export default function FlightSearchScreen() {
  const router = useRouter();

  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [departureDate, setDepartureDate] = useState("");
  const [returnDate, setReturnDate] = useState("");

  const handleSearch = () => {
    router.push({
      pathname: "/flights/results",
      params: { origin, destination, departureDate, returnDate },
    });
  };

  return (
    <View className="flex-1 bg-gray-50 p-6">
      <Text className="text-2xl font-bold mb-6">Search Flights</Text>

      {/* Origin */}
      <View className="mb-4">
        <Text className="mb-1 text-gray-600">From</Text>
        <TextInput
          placeholder="Lagos (LOS)"
          value={origin}
          onChangeText={setOrigin}
          className="bg-white p-4 rounded-2xl border border-gray-200"
        />
      </View>

      {/* Destination */}
      <View className="mb-4">
        <Text className="mb-1 text-gray-600">To</Text>
        <TextInput
          placeholder="London (LHR)"
          value={destination}
          onChangeText={setDestination}
          className="bg-white p-4 rounded-2xl border border-gray-200"
        />
      </View>

      {/* Dates */}
      <View className="mb-4">
        <Text className="mb-1 text-gray-600">Departure Date</Text>
        <TextInput
          placeholder="YYYY-MM-DD"
          value={departureDate}
          onChangeText={setDepartureDate}
          className="bg-white p-4 rounded-2xl border border-gray-200"
        />
      </View>

      <View className="mb-6">
        <Text className="mb-1 text-gray-600">Return Date (Optional)</Text>
        <TextInput
          placeholder="YYYY-MM-DD"
          value={returnDate}
          onChangeText={setReturnDate}
          className="bg-white p-4 rounded-2xl border border-gray-200"
        />
      </View>

      {/* Search Button */}
      <TouchableOpacity
        onPress={handleSearch}
        className="bg-blue-600 py-4 rounded-2xl items-center"
      >
        <Text className="text-white font-semibold text-lg">Search Flights</Text>
      </TouchableOpacity>
    </View>
  );
}
