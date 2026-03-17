import { PressableOpacity } from "@/components/ui/pressable-opacity";
import { useHotelsQuery } from "@/lib/hooks/hotels/use-hotels-query";
import { useRouter } from "expo-router";
import { useState } from "react";
import { FlatList, Text, TextInput, View } from "react-native";

export default function HotelSearchScreen() {
  const [city, setCity] = useState("");
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const router = useRouter();

  const hotelsQuery = useHotelsQuery({ city, checkIn, checkOut });

  return (
    <View className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-4">Search Hotels</Text>
      <TextInput placeholder="City" value={city} onChangeText={setCity} className="bg-white p-3 rounded-xl mb-2" />
      <TextInput placeholder="Check In (YYYY-MM-DD)" value={checkIn} onChangeText={setCheckIn} className="bg-white p-3 rounded-xl mb-2" />
      <TextInput placeholder="Check Out (YYYY-MM-DD)" value={checkOut} onChangeText={setCheckOut} className="bg-white p-3 rounded-xl mb-4" />

      <PressableOpacity className="bg-blue-600 py-3 rounded-xl mb-4" onPress={() => void hotelsQuery.refetch()}>
        <Text className="text-white text-center font-semibold">Search</Text>
      </PressableOpacity>

      <FlatList
        data={hotelsQuery.data ?? []}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <PressableOpacity
            className="bg-white rounded-2xl p-4 mb-4 shadow"
            onPress={() =>
              router.push({
                pathname: "/hotels/book/[id]",
                params: { id: item.id.toString(), checkIn, checkOut, guests: "1" },
              })
            }
          >
            <Text className="text-lg font-semibold">{item.hotel_name}</Text>
            <Text className="text-gray-500">{item.city}</Text>
          </PressableOpacity>
        )}
      />
    </View>
  );
}
