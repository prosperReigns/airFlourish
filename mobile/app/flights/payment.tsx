import { api } from "@/services/api";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Text, TouchableOpacity, View } from "react-native";
import { WebView } from "react-native-webview";

const router = useRouter();

export default function PaymentScreen() {
  const { flight, passenger } = useLocalSearchParams();
  const parsedFlight = JSON.parse(flight as string);
  const parsedPassenger = JSON.parse(passenger as string);

  const [checkoutUrl, setCheckoutUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handlePayment = async () => {
    setLoading(true);

    try {
      const response = await api.post("/payments/init/", {
        amount: parsedFlight.price.total,
        currency: parsedFlight.price.currency,
        tx_ref: `FL-${Date.now()}`,
        meta: {
          flight_offer: parsedFlight,
          travelers: [
            {
              id: "1",
              dateOfBirth: parsedPassenger.dob,
              name: {
                firstName: parsedPassenger.firstName,
                lastName: parsedPassenger.lastName,
              },
            },
          ],
        },
      });

      setCheckoutUrl(response.data.link);
    } catch (err) {
      console.log(err);
    } finally {
      setLoading(false);
    }
  };

  if (checkoutUrl) {
    return (
      <WebView
        source={{ uri: checkoutUrl }}
        onNavigationStateChange={(navState) => {
          if (navState.url.includes("payment-success")) {
            router.replace("/flights/success");
          }
        }}
      />
    );
  }

  return (
    <View className="flex-1 bg-gray-50 p-6 justify-center">
      <Text className="text-2xl font-bold mb-4 text-center">
        Confirm Payment
      </Text>

      <Text className="text-center mb-6">
        Amount: {parsedFlight.price.total} {parsedFlight.price.currency}
      </Text>

      {loading ? (
        <ActivityIndicator size="large" />
      ) : (
        <TouchableOpacity
          onPress={handlePayment}
          className="bg-blue-600 py-4 rounded-2xl items-center"
        >
          <Text className="text-white font-semibold text-lg">Pay Now</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}
