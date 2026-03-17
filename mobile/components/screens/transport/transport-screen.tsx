import { useRouter } from "expo-router";
import { FlatList, Text, View } from "react-native";

import { PressableOpacity } from "@/components/ui/pressable-opacity";
import { useTransportOptionsQuery } from "@/lib/hooks/transport/use-transport-options-query";

export default function TransportScreen() {
  const router = useRouter();
  const { data: transports = [] } = useTransportOptionsQuery();

  return (
    <View className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-6">Transport Services</Text>
      <FlatList
        data={transports}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <PressableOpacity
            className="bg-white rounded-2xl p-4 mb-4 shadow"
            onPress={() => router.push(`/transport/book/${item.id}`)}
          >
            <Text className="text-lg font-semibold">{item.transport_name}</Text>
            <Text className="text-gray-500">{item.pickup_location} → {item.dropoff_location}</Text>
          </PressableOpacity>
        )}
      />
    </View>
  );
}
