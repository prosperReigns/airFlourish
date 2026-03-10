import { useRouter } from "expo-router";
import { useState } from "react";
import { Button, TextInput, View } from "react-native";
import API from "@/services/api";

export default function FlightSearch() {
  const router = useRouter();
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState("");

  const searchFlights = async () => {
    const response = await API.get("flights/search/", {
      params: {
        origin,
        destination,
        departure_date: date,
      },
    });

    router.push({
      pathname: "/flights/results",
      params: { data: JSON.stringify(response.data) },
    });
  };

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

      <Button title="Search Flights" onPress={searchFlights} />
    </View>
  );
}
