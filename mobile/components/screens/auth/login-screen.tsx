import { useRouter } from "expo-router";
import { ActivityIndicator, Text, View } from "react-native";
import { useState } from "react";

import Input from "@/components/ui/Input";
import { useLoginMutation } from "@/lib/hooks/auth/use-login-mutation";
import { PressableOpacity } from "@/components/ui/pressable-opacity";

export function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const loginMutation = useLoginMutation();

  const handleLogin = async () => {
    try {
      await loginMutation.mutateAsync({ email, password });
      router.replace("/(tabs)");
    } catch (error) {
      console.log(error);
    }
  };

  return (
    <View className="flex-1 bg-gray-50 justify-center items-center px-6 w-full">
      <View className="bg-white p-8 rounded-3xl shadow-lg">
        <Text className="text-3xl font-bold mb-2 text-center">Welcome Back</Text>
        <Text className="text-gray-500 text-center mb-8">Login to continue</Text>

        <Input placeholder="Email" value={email} onChangeText={setEmail} />
        <Input
          placeholder="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <PressableOpacity
          onPress={handleLogin}
          className="bg-blue-600 p-4 rounded-2xl mt-4"
        >
          {loginMutation.isPending ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text className="text-white text-center font-semibold w-full text-lg">
              Login
            </Text>
          )}
        </PressableOpacity>

        <PressableOpacity
          onPress={() => router.push("/(auth)/register")}
          className="mt-6"
        >
          <Text className="text-center text-gray-600">
            Don’t have an account? <Text className="text-blue-600 font-semibold">Register</Text>
          </Text>
        </PressableOpacity>
      </View>
    </View>
  );
}
