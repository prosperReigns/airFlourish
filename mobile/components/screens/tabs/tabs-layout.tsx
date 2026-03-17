import { Ionicons } from "@expo/vector-icons";
import { createDrawerNavigator } from "@react-navigation/drawer";
import { Tabs, useRouter } from "expo-router";
import { Text, View } from "react-native";

import { useLogoutMutation } from "@/lib/hooks/auth/use-logout-mutation";
import { PressableOpacity } from "@/components/ui/pressable-opacity";

const Drawer = createDrawerNavigator();

function CustomDrawerContent() {
  const router = useRouter();
  const logoutMutation = useLogoutMutation();

  const handleLogout = async () => {
    await logoutMutation.mutateAsync();
    router.replace("/(auth)/login");
  };

  return (
    <View style={{ flex: 1, paddingTop: 60 }}>
      <Text style={{ fontSize: 20, fontWeight: "bold", marginLeft: 20 }}>Welcome</Text>
      <PressableOpacity style={{ marginTop: 40, marginLeft: 20 }} onPress={() => router.push("/profile")}>
        <Text>Profile</Text>
      </PressableOpacity>
      <PressableOpacity style={{ marginTop: 20, marginLeft: 20 }} onPress={() => router.push("/settings")}>
        <Text>Settings</Text>
      </PressableOpacity>
      <PressableOpacity style={{ marginTop: 20, marginLeft: 20 }} onPress={handleLogout}>
        <Text style={{ color: "red" }}>Logout</Text>
      </PressableOpacity>
    </View>
  );
}

function BottomTabs() {
  return (
    <Tabs
      screenOptions={({ navigation }) => ({
        headerLeft: () => (
          <PressableOpacity style={{ marginLeft: 15 }} onPress={() => navigation.toggleDrawer()}>
            <Ionicons name="menu" size={28} />
          </PressableOpacity>
        ),
        tabBarActiveTintColor: "#2563EB",
      })}
    >
      <Tabs.Screen name="index" options={{ title: "Home" }} />
      <Tabs.Screen name="bookings" />
      <Tabs.Screen name="flights" />
      <Tabs.Screen name="payments" />
      <Tabs.Screen name="profile" />
      <Tabs.Screen name="settings" />
    </Tabs>
  );
}

export function TabsLayoutScreen() {
  return (
    <Drawer.Navigator
      screenOptions={{ headerShown: false }}
      drawerContent={() => <CustomDrawerContent />}
    >
      <Drawer.Screen name="Main" component={BottomTabs} />
    </Drawer.Navigator>
  );
}
