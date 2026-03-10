import axios from "axios";
import { useRouter } from "expo-router";
import { useState } from "react";
import { Text, TextInput, TouchableOpacity, View } from "react-native";

export default function VisaApplicationScreen() {
  const [country, setCountry] = useState("");
  const [visaType, setVisaType] = useState("");
  const [applicantName, setApplicantName] = useState("");
  const router = useRouter();

  const applyVisa = () => {
    axios
      .post("https://192.168.0.200:8000/api/visa/", {
        country,
        visa_type: visaType,
        applicant_name: applicantName,
        issue_date: "2026-03-01",
        expiry_date: "2027-03-01",
        visa_fee: 50000,
      })
      .then((res) => router.push("/bookings"))
      .catch((err) => console.log(err));
  };

  return (
    <View className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-4">Visa Application</Text>
      <TextInput
        placeholder="Country"
        value={country}
        onChangeText={setCountry}
        className="bg-white p-3 rounded-xl mb-2"
      />
      <TextInput
        placeholder="Visa Type"
        value={visaType}
        onChangeText={setVisaType}
        className="bg-white p-3 rounded-xl mb-2"
      />
      <TextInput
        placeholder="Applicant Name"
        value={applicantName}
        onChangeText={setApplicantName}
        className="bg-white p-3 rounded-xl mb-4"
      />

      <TouchableOpacity
        className="bg-blue-600 py-3 rounded-xl"
        onPress={applyVisa}
      >
        <Text className="text-white text-center font-semibold">Apply</Text>
      </TouchableOpacity>
    </View>
  );
}
