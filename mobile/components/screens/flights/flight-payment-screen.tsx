import { PressableOpacity } from "@/components/ui/pressable-opacity";
import { useSecureFlightBookingMutation } from "@/lib/hooks/flights/use-secure-flight-booking-mutation";
import { useLocalSearchParams, useRouter } from "expo-router";
import { ActivityIndicator, Text, View } from "react-native";
import { WebView } from "react-native-webview";

export default function FlightPaymentScreen() {
  const router = useRouter();
  const { flight, passenger } = useLocalSearchParams();
  const parsedFlight = JSON.parse(flight as string);
  const parsedPassenger = JSON.parse(passenger as string);

  const secureBookMutation = useSecureFlightBookingMutation();
  const checkoutUrl = secureBookMutation.data?.payment_link ?? null;

  const handlePayment = async () => {
    try {
      await secureBookMutation.mutateAsync({
        flightOffer: parsedFlight,
        passenger: parsedPassenger,
      });
    } catch (error) {
      console.log(error);
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
      <Text className="text-2xl font-bold mb-4 text-center">Confirm Payment</Text>
      <Text className="text-center mb-6">
        Amount: {parsedFlight.price.total} {parsedFlight.price.currency}
      </Text>

      {secureBookMutation.isPending ? (
        <ActivityIndicator size="large" />
      ) : (
        <PressableOpacity
          onPress={handlePayment}
          className="bg-blue-600 py-4 rounded-2xl items-center"
        >
          <Text className="text-white font-semibold text-lg">Pay Now</Text>
        </PressableOpacity>
      )}
    </View>
  );
}
