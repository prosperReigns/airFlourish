import { useAuthStore } from "@/store/authStore";
import { Text, TouchableOpacity, View } from "react-native";

export default function ProfileScreen() {
  const { logout } = useAuthStore();

  return (
    <View className="flex-1 bg-gray-50 p-5">
      <Text className="text-2xl font-bold mb-6">Profile</Text>

      <TouchableOpacity onPress={logout} className="bg-red-500 p-4 rounded-xl">
        <Text className="text-white text-center font-semibold">Logout</Text>
      </TouchableOpacity>
    </View>
  );
}
