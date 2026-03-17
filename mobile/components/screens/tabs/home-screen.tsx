import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { ScrollView, Text, View } from "react-native";
import { PressableOpacity } from "@/components/ui/pressable-opacity";

export default function HomeScreen() {
  return (
    <ScrollView className="flex-1 bg-gray-50 p-5">
      <Text className="text-2xl font-bold mb-6">Welcome 👋</Text>

      {/* Flights */}
      <PressableOpacity
        onPress={() => router.push("/flights")}
        className="bg-white p-5 rounded-2xl mb-4 shadow"
      >
        <View className="flex-row items-center">
          <Ionicons name="airplane-outline" size={24} color="#2563EB" />
          <Text className="ml-3 text-lg font-semibold">Book Flight</Text>
        </View>
      </PressableOpacity>

      {/* Hotels */}
      <PressableOpacity
        onPress={() => router.push("/hotels")}
        className="bg-white p-5 rounded-2xl mb-4 shadow"
      >
        <View className="flex-row items-center">
          <Ionicons name="bed-outline" size={24} color="#2563EB" />
          <Text className="ml-3 text-lg font-semibold">Reserve Hotel</Text>
        </View>
      </PressableOpacity>

      {/* Transport */}
      <PressableOpacity
        onPress={() => router.push("/transport")}
        className="bg-white p-5 rounded-2xl mb-4 shadow"
      >
        <View className="flex-row items-center">
          <Ionicons name="car-outline" size={24} color="#2563EB" />
          <Text className="ml-3 text-lg font-semibold">Transport</Text>
        </View>
      </PressableOpacity>

      {/* Visa */}
      <PressableOpacity
        onPress={() => router.push("/visa")}
        className="bg-white p-5 rounded-2xl shadow"
      >
        <View className="flex-row items-center">
          <Ionicons name="document-outline" size={24} color="#2563EB" />
          <Text className="ml-3 text-lg font-semibold">Visa Application</Text>
        </View>
      </PressableOpacity>
    </ScrollView>
  );
}
