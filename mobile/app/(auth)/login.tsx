import Input from "@/components/ui/Input";
import { useAuthStore } from "@/store/authStore";
import { useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Text, TouchableOpacity, View } from "react-native";

export default function LoginScreen({ setUserToken }: { setUserToken: (token: string) => void }) {
    const router = useRouter();
    const { login } = useAuthStore();

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);

    const handleLogin = async () => {
      try {
        setLoading(true);
        const token = await login(username, password);
        setUserToken(token); //update AppNavigator
      } catch (error) {
        console.log(error);
      } finally {
        setLoading(false);
      }
    };

    return (
      <View className="flex-1 bg-gray-50 justify-center items-center px-6 w-full">
        <View className="bg-white p-8 rounded-3xl shadow-lg">
          <Text className="text-3xl font-bold mb-2 text-center">
            Welcome Back
          </Text>

          <Text className="text-gray-500 text-center mb-8">
            Login to continue
          </Text>

          <Input placeholder="Username" value={username} onChangeText={setUsername} />

          <Input
            placeholder="Password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />

          <TouchableOpacity
            onPress={handleLogin}
            className="bg-blue-600 p-4 rounded-2xl mt-4"
          >
            {loading ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text className="text-white text-center font-semibold w-full bg-red-500 text-lg rounded">
                Login
              </Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => router.push("/(auth)/register")}
            className="mt-6"
          >
            <Text className="text-center text-gray-600">
              Don’t have an account?{" "}
              <Text className="text-blue-600 font-semibold">Register</Text>
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    );
}
