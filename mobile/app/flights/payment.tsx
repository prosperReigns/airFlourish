import { api } from "@/services/api";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Text, TouchableOpacity, View } from "react-native";
import { WebView } from "react-native-webview";

export default function PaymentScreen() {
  const router = useRouter();
  const { flight, passenger } = useLocalSearchParams();
  const parsedFlight = JSON.parse(flight as string);
  const parsedPassenger = JSON.parse(passenger as string);

  const [checkoutUrl, setCheckoutUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handlePayment = async () => {
    setLoading(true);

    try {
      const departureSegment = parsedFlight.itineraries?.[0]?.segments?.[0];
      const arrivalSegment = parsedFlight.itineraries?.[0]?.segments?.slice(-1)[0];

      const returnSegment =
        parsedFlight.itineraries?.[1]?.segments?.slice(-1)[0];

      const response = await api.post("flights/secure-book/", {
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
        departure_city: departureSegment?.departure?.iataCode,
        arrival_city: arrivalSegment?.arrival?.iataCode,
        departure_date: departureSegment?.departure?.at?.split("T")[0],
        return_date: returnSegment?.arrival?.at
          ? returnSegment.arrival.at.split("T")[0]
          : null,
        airline: parsedFlight.validatingAirlineCodes?.[0],
        passengers: 1,
      });

      if (!response.data?.payment_link) {
        throw new Error("Payment link not provided");
      }
      setCheckoutUrl(response.data.payment_link);
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
