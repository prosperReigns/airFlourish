import { api } from "@/services/api";
import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { FlatList, Text, TouchableOpacity, View } from "react-native";

interface Transport {
  id: number;
  transport_name: string;
  pickup_location: string;
  dropoff_location: string;
  price_per_passenger: number;
  currency: string;
  passengers: number;
}

export default function TransportScreen() {
  const [transports, setTransports] = useState<Transport[]>([]);
  const router = useRouter();

  useEffect(() => {
    api
      .get("transport/transport-options/")
      .then((res) => setTransports(res.data))
      .catch((err) => console.log(err));
  }, []);

  const renderItem = ({ item }: { item: Transport }) => (
    <TouchableOpacity
      className="bg-white rounded-2xl p-4 mb-4 shadow"
      onPress={() => router.push(`/transport/book/${item.id}`)}
    >
      <Text className="text-lg font-semibold">{item.transport_name}</Text>
      <Text className="text-gray-500">
        {item.pickup_location} → {item.dropoff_location}
      </Text>
      <Text className="text-gray-700 mt-1">
        {item.currency ?? "NGN"} {item.price_per_passenger}
      </Text>
      <Text className="text-gray-500 mt-1">
        Passengers: {item.passengers}
      </Text>
    </TouchableOpacity>
  );

  return (
    <View className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-6">Transport Services</Text>
      <FlatList
        data={transports}
        keyExtractor={(item) => item.transport_id}
        renderItem={renderItem}
      />
    </View>
  );
}
