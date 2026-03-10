import { Text, View } from "react-native";

export default function PaymentsScreen() {
  return (
    <View className="flex-1 bg-gray-50 p-5">
      <Text className="text-2xl font-bold mb-4">Payments</Text>

      <View className="bg-white p-4 rounded-2xl shadow">
        <Text>No payments yet.</Text>
      </View>
    </View>
  );
}
