import { Tabs } from "expo-router";
import { createDrawerNavigator } from "@react-navigation/drawer";
import { Ionicons } from "@expo/vector-icons";
import { TouchableOpacity, View, Text } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useRouter } from "expo-router";

const Drawer = createDrawerNavigator();

function CustomDrawerContent(props: any) {
  const router = useRouter();

  const logout = async () => {
    await AsyncStorage.removeItem("access_token");
    await AsyncStorage.removeItem("refresh_token");
    router.replace("/(auth)/login");
  };

  return (
    <View style={{ flex: 1, paddingTop: 60 }}>
      <Text style={{ fontSize: 20, fontWeight: "bold", marginLeft: 20 }}>
        Welcome
      </Text>

      <TouchableOpacity
        style={{ marginTop: 40, marginLeft: 20 }}
        onPress={() => router.push("/profile")}
      >
        <Text>Profile</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={{ marginTop: 20, marginLeft: 20 }}
        onPress={() => router.push("/settings")}
      >
        <Text>Settings</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={{ marginTop: 20, marginLeft: 20 }}
        onPress={logout}
      >
        <Text style={{ color: "red" }}>Logout</Text>
      </TouchableOpacity>
    </View>
  );
}

function BottomTabs() {
  return (
    <Tabs
      screenOptions={({ navigation }) => ({
        headerLeft: () => (
          <TouchableOpacity
            style={{ marginLeft: 15 }}
            onPress={() => navigation.toggleDrawer()}
          >
            <Ionicons name="menu" size={28} />
          </TouchableOpacity>
        ),
        tabBarActiveTintColor: "#2563EB",
      })}
    >
      <Tabs.Screen name="index" options={{ title: "Home" }} />
      <Tabs.Screen name="bookings" />
      <Tabs.Screen name="visa" />
      <Tabs.Screen name="transport" />
    </Tabs>
  );
}

export default function Layout() {
  return (
    <Drawer.Navigator
      screenOptions={{ headerShown: false }}
      drawerContent={(props) => <CustomDrawerContent {...props} />}
    >
      <Drawer.Screen name="Main" component={BottomTabs} />
    </Drawer.Navigator>
  );
}