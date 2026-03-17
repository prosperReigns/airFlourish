import { useRouter } from "expo-router";
import { useState } from "react";
import { Alert, Text, TextInput, View } from "react-native";

import { PressableOpacity } from "@/components/ui/pressable-opacity";
import { useCreateVisaApplicationMutation } from "@/lib/hooks/visa/use-create-visa-application-mutation";

export default function VisaApplicationScreen() {
  const router = useRouter();
  const mutation = useCreateVisaApplicationMutation();

  const [country, setCountry] = useState("");
  const [visaType, setVisaType] = useState("");
  const [appointmentDate, setAppointmentDate] = useState("");
  const [visaFee, setVisaFee] = useState("");

  const applyVisa = async () => {
    if (appointmentDate && !/^\d{4}-\d{2}-\d{2}$/.test(appointmentDate)) {
      Alert.alert("Invalid date", "Use YYYY-MM-DD for the appointment date.");
      return;
    }

    try {
      await mutation.mutateAsync({
        destinationCountry: country,
        visaType,
        appointmentDate,
        visaFee: Number(visaFee) || 0,
      });
      router.push("/bookings");
    } catch (error) {
      console.log(error);
    }
  };

  return (
    <View className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-4">Visa Application</Text>
      <TextInput placeholder="Country" value={country} onChangeText={setCountry} className="bg-white p-3 rounded-xl mb-2" />
      <TextInput placeholder="Visa Type" value={visaType} onChangeText={setVisaType} className="bg-white p-3 rounded-xl mb-2" />
      <TextInput placeholder="Appointment Date (YYYY-MM-DD)" value={appointmentDate} onChangeText={setAppointmentDate} className="bg-white p-3 rounded-xl mb-2" />
      <TextInput placeholder="Visa Fee (NGN)" value={visaFee} onChangeText={setVisaFee} keyboardType="numeric" className="bg-white p-3 rounded-xl mb-4" />

      <PressableOpacity className="bg-blue-600 py-3 rounded-xl" onPress={applyVisa}>
        <Text className="text-white text-center font-semibold">Apply</Text>
      </PressableOpacity>
    </View>
  );
}
