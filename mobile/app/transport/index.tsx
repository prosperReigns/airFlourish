import axios from "axios";
import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { FlatList, Text, TouchableOpacity, View } from "react-native";

interface Transport {
  transport_id: string;
  transport_name: string;
  departure: string;
  arrival: string;
  date: string;
  seats: number;
  price: number;
}

export default function TransportScreen() {
  const [transports, setTransports] = useState<Transport[]>([]);
  const router = useRouter();

  useEffect(() => {
    axios
      .get("https://192.168.0.200:8000/api/transport/")
      .then((res) => setTransports(res.data))
      .catch((err) => console.log(err));
  }, []);

  const renderItem = ({ item }: { item: Transport }) => (
    <TouchableOpacity
      className="bg-white rounded-2xl p-4 mb-4 shadow"
      onPress={() => router.push(`/transport/book/${item.transport_id}`)}
    >
      <Text className="text-lg font-semibold">{item.transport_name}</Text>
      <Text className="text-gray-500">
        {item.departure} → {item.arrival}
      </Text>
      <Text className="text-gray-700 mt-1">NGN {item.price}</Text>
      <Text className="text-gray-500 mt-1">Seats: {item.seats}</Text>
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
