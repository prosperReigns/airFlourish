import { useRouter } from "expo-router";
import { Text, TouchableOpacity, View } from "react-native";

export default function BookingSuccessScreen() {
  const router = useRouter();

  return (
    <View className="flex-1 bg-gray-50 justify-center items-center px-6">
      {/* Success Icon */}
      <View className="w-24 h-24 bg-green-100 rounded-full justify-center items-center mb-6">
        <Text className="text-4xl">✓</Text>
      </View>

      <Text className="text-2xl font-bold text-center mb-3">
        Payment Successful 🎉
      </Text>

      <Text className="text-gray-500 text-center mb-8">
        Your booking is being processed. You will receive confirmation shortly.
      </Text>

      <TouchableOpacity
        onPress={() => router.replace("/bookings")}
        className="bg-blue-600 py-4 px-10 rounded-2xl mb-4"
      >
        <Text className="text-white font-semibold text-lg">
          View My Bookings
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        onPress={() => router.replace("/home")}
        className="py-3"
      >
        <Text className="text-blue-600 font-medium">Back to Home</Text>
      </TouchableOpacity>
    </View>
  );
}
