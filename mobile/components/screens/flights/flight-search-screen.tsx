import { useRouter } from "expo-router";
import { useState } from "react";
import { Text, TextInput, View } from "react-native";

import { PressableOpacity } from "@/components/ui/pressable-opacity";

export default function FlightSearchScreen() {
  const router = useRouter();
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState("");

  return (
    <View className="flex-1 p-6">
      <TextInput
        placeholder="Origin (Lagos)"
        value={origin}
        onChangeText={setOrigin}
        className="border p-3 rounded mb-4"
      />
      <TextInput
        placeholder="Destination (London)"
        value={destination}
        onChangeText={setDestination}
        className="border p-3 rounded mb-4"
      />
      <TextInput
        placeholder="Departure Date (YYYY-MM-DD)"
        value={date}
        onChangeText={setDate}
        className="border p-3 rounded mb-4"
      />

      <PressableOpacity
        className="bg-blue-600 py-3 rounded-xl"
        onPress={() =>
          router.push({
            pathname: "/flights/results",
            params: { origin, destination, departureDate: date },
          })
        }
      >
        <Text className="text-white text-center font-semibold">Search Flights</Text>
      </PressableOpacity>
    </View>
  );
}
