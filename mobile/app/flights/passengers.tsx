import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { Text, TextInput, TouchableOpacity, View } from "react-native";

export default function PassengerScreen() {
  const router = useRouter();
  const { flight } = useLocalSearchParams();
  const parsedFlight = JSON.parse(flight as string);

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [dob, setDob] = useState("");

  const handleContinue = () => {
    router.push({
      pathname: "/flights/payment",
      params: {
        flight: JSON.stringify(parsedFlight),
        passenger: JSON.stringify({ firstName, lastName, dob }),
      },
    });
  };

  return (
    <View className="flex-1 bg-gray-50 p-6">
      <Text className="text-2xl font-bold mb-6">Passenger Details</Text>

      <TextInput
        placeholder="First Name"
        value={firstName}
        onChangeText={setFirstName}
        className="bg-white p-4 rounded-2xl mb-4"
      />

      <TextInput
        placeholder="Last Name"
        value={lastName}
        onChangeText={setLastName}
        className="bg-white p-4 rounded-2xl mb-4"
      />

      <TextInput
        placeholder="Date of Birth (YYYY-MM-DD)"
        value={dob}
        onChangeText={setDob}
        className="bg-white p-4 rounded-2xl mb-6"
      />

      <TouchableOpacity
        onPress={handleContinue}
        className="bg-blue-600 py-4 rounded-2xl items-center"
      >
        <Text className="text-white font-semibold text-lg">
          Continue to Payment
        </Text>
      </TouchableOpacity>
    </View>
  );
}
