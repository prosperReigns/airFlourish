import { useRouter } from "expo-router";
import { ActivityIndicator, Text, View } from "react-native";
import { useState } from "react";

import Input from "@/components/ui/Input";
import { useRegisterMutation } from "@/lib/hooks/auth/use-register-mutation";
import { PressableOpacity } from "@/components/ui/pressable-opacity";

export function RegisterScreen() {
  const router = useRouter();
  const registerMutation = useRegisterMutation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");

  const handleRegister = async () => {
    try {
      await registerMutation.mutateAsync({
        first_name: firstName,
        last_name: lastName || "",
        email,
        password,
        user_type: "regular",
      });
      router.replace("/(auth)/login");
    } catch (error) {
      console.log(error);
    }
  };

  return (
    <View className="flex-1 bg-gray-50 justify-center items-center px-6 w-full">
      <View className="bg-white p-8 rounded-3xl shadow-lg">
        <Text className="text-3xl font-bold mb-2 text-center">Create Account</Text>
        <Text className="text-gray-500 text-center mb-8">Join the travel platform</Text>

        <Input placeholder="First Name" value={firstName} onChangeText={setFirstName} />
        <Input placeholder="Last Name" value={lastName} onChangeText={setLastName} />
        <Input placeholder="Email" value={email} onChangeText={setEmail} />
        <Input
          placeholder="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <PressableOpacity
          onPress={handleRegister}
          className="bg-red-600 p-4 rounded-2xl mt-4"
        >
          {registerMutation.isPending ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text className="text-white text-center font-semibold text-lg">Register</Text>
          )}
        </PressableOpacity>

        <PressableOpacity onPress={() => router.push("/(auth)/login")} className="mt-6">
          <Text className="text-center text-gray-600">
            Already have an account? <Text className="text-blue-600 font-semibold">Login</Text>
          </Text>
        </PressableOpacity>
      </View>
    </View>
  );
}
