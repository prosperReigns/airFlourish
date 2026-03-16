import { fetchProfile } from "@/services/auth";
import { useAuthStore } from "@/store/authStore";
import { useEffect, useState } from "react";
import { ActivityIndicator, Text, TouchableOpacity, View } from "react-native";

export default function ProfileScreen() {
  const { logout, user } = useAuthStore();
  const [profile, setProfile] = useState(user);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const data = await fetchProfile();
        setProfile(data);
      } catch {
        setError("Unable to load profile details.");
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, []);

  return (
    <View className="flex-1 bg-gray-50 p-5">
      <Text className="text-2xl font-bold mb-6">Profile</Text>

      {loading ? (
        <View className="items-center justify-center py-10">
          <ActivityIndicator size="large" />
        </View>
      ) : error ? (
        <View className="bg-white p-4 rounded-2xl shadow mb-6">
          <Text className="text-red-500 text-center">{error}</Text>
        </View>
      ) : (
        <View className="bg-white p-4 rounded-2xl shadow mb-6">
          <Text className="text-lg font-semibold mb-2">
            {profile?.first_name ?? ""} {profile?.last_name ?? ""}
          </Text>
          <Text className="text-gray-600 mb-1">{profile?.email}</Text>
          {profile?.phone_number ? (
            <Text className="text-gray-600 mb-1">
              {profile?.phone_number}
            </Text>
          ) : null}
          {profile?.country?.name ? (
            <Text className="text-gray-600">{profile?.country?.name}</Text>
          ) : null}
        </View>
      )}

      <TouchableOpacity
        onPress={logout}
        className="bg-red-500 p-4 rounded-xl"
      >
        <Text className="text-white text-center font-semibold">Logout</Text>
      </TouchableOpacity>
    </View>
  );
}
