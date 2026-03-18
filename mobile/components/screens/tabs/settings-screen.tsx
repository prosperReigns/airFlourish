import { useState } from "react";
import { useNavigation } from "@react-navigation/native";
import { ScrollView, Switch, Text, View } from "react-native";
import { PressableOpacity } from "@/components/ui/pressable-opacity";

export default function SettingsScreen() {
  const navigation = useNavigation();
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  return (
    <ScrollView className="flex-1 bg-white p-6">
      <Text className="text-2xl font-bold mb-6">Settings</Text>

      {/* Dark Mode */}
      <View className="flex-row justify-between items-center mb-4">
        <Text className="text-lg">Dark Mode</Text>
        <Switch
          value={isDarkMode}
          onValueChange={() => setIsDarkMode(!isDarkMode)}
        />
      </View>

      {/* Notifications */}
      <View className="flex-row justify-between items-center mb-4">
        <Text className="text-lg">Enable Notifications</Text>
        <Switch
          value={notificationsEnabled}
          onValueChange={() =>
            setNotificationsEnabled(!notificationsEnabled)
          }
        />
      </View>

      {/* Account & Security */}
      <PressableOpacity
        className="py-4 border-b border-gray-200"
        onPress={() => navigation.navigate("Profile")}
      >
        <Text className="text-lg">Account & Security</Text>
      </PressableOpacity>

      {/* Payment Methods */}
      <PressableOpacity
        className="py-4 border-b border-gray-200"
        onPress={() => navigation.navigate("Payments")}
      >
        <Text className="text-lg">Payment Methods</Text>
      </PressableOpacity>

      {/* Help & Support */}
      <PressableOpacity
        className="py-4 border-b border-gray-200"
        onPress={() => alert("Help & Support")}
      >
        <Text className="text-lg">Help & Support</Text>
      </PressableOpacity>

      {/* Logout */}
      <PressableOpacity
        className="py-4 border-b border-gray-200 mt-6"
        onPress={() => alert("Logout")}
      >
        <Text className="text-lg text-red-500">Logout</Text>
      </PressableOpacity>
    </ScrollView>
  );
}