import { ActivityIndicator, Text, View } from "react-native";

import { PressableOpacity } from "@/components/ui/pressable-opacity";
import { useAuth } from "@/hooks/use-auth";
import { useProfileQuery } from "@/lib/hooks/auth/use-profile-query";

export default function TabProfileScreen() {
  const { logout, user } = useAuth();
  const { data: profile, isLoading, error } = useProfileQuery();

  const currentProfile = profile ?? user;

  return (
    <View className="flex-1 bg-gray-50 p-5">
      <Text className="text-2xl font-bold mb-6">Profile</Text>

      {isLoading ? (
        <View className="items-center justify-center py-10">
          <ActivityIndicator size="large" />
        </View>
      ) : error ? (
        <View className="bg-white p-4 rounded-2xl shadow mb-6">
          <Text className="text-red-500 text-center">Unable to load profile details.</Text>
        </View>
      ) : (
        <View className="bg-white p-4 rounded-2xl shadow mb-6">
          <Text className="text-lg font-semibold mb-2">
            {currentProfile?.first_name ?? ""} {currentProfile?.last_name ?? ""}
          </Text>
          <Text className="text-gray-600 mb-1">{currentProfile?.email}</Text>
        </View>
      )}

      <PressableOpacity onPress={logout} className="bg-red-500 p-4 rounded-xl">
        <Text className="text-white text-center font-semibold">Logout</Text>
      </PressableOpacity>
    </View>
  );
}
