import { View, Text, TouchableOpacity, ActivityIndicator } from "react-native";
import { useState } from "react";
import { useRouter } from "expo-router";
import Input from "@/components/ui/Input";
import API from "@/services/api";

export default function RegisterScreen() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [first_name, setFirstName] = useState("");
  const [last_name, setLastName] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    try {
      setLoading(true);

      await API.post("users/register/", {
        first_name: first_name,
        last_name: last_name || "",
        email,
        password,
        user_type: "regular", // optional default
      });

      router.replace("/(auth)/login");
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
          Create Account
        </Text>

        <Text className="text-gray-500 text-center mb-8">
          Join the travel platform
        </Text>

        <Input
          placeholder="First Name"
          value={first_name}
          onChangeText={setFirstName}
        />

        <Input
          placeholder="Last Name"
          value={last_name}
          onChangeText={setLastName}
        />

        <Input
          placeholder="Email"
          value={email}
          onChangeText={setEmail}
        />

        <Input
          placeholder="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity
          onPress={handleRegister}
          className="bg-red-600 p-4 rounded-2xl mt-4"
        >
          {loading ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text className="text-white text-center font-semibold text-lg bg-red-500 rounded w-full">
              Register
            </Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          onPress={() => router.push("/(auth)/login")}
          className="mt-6"
        >
          <Text className="text-center text-gray-600">
            Already have an account?{" "}
            <Text className="text-blue-600 font-semibold">Login</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}