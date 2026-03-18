import * as Linking from "expo-linking";
import { useLocalSearchParams } from "expo-router";
import { useMemo } from "react";
import { Alert, Text, View } from "react-native";

import { createIdempotencyKey } from "@/lib/api/payments";
import { useBookingQuery } from "@/lib/hooks/bookings/use-booking-query";
import { useInitiateCardPaymentMutation } from "@/lib/hooks/payments/use-initiate-card-payment-mutation";
import { PressableOpacity } from "@/components/ui/pressable-opacity";

export function PaymentScreen() {
  const { bookingId } = useLocalSearchParams<{ bookingId?: string | string[] }>();
  const bookingIdValue = useMemo(
    () => (Array.isArray(bookingId) ? bookingId[0] : bookingId),
    [bookingId],
  );

  const { data: booking } = useBookingQuery(bookingIdValue);
  const paymentMutation = useInitiateCardPaymentMutation();

  const handlePayment = async () => {
    if (!booking) return;

    const txRef = `PAY-${booking.reference_code}-${Date.now()}`;
    const currency = booking.currency ?? "NGN";
    const amount = booking.total_price;

    if (amount === null || amount === undefined) {
      Alert.alert("Payment Error", "Missing booking amount.");
      return;
    }

    try {
      const res = await paymentMutation.mutateAsync({
        bookingId: booking.id,
        amount,
        currency,
        txRef,
        idempotencyKey: createIdempotencyKey(),
      });

      const paymentLink = res.gateway?.link;
      if (!paymentLink) {
        throw new Error("Payment link missing");
      }

      await Linking.openURL(paymentLink);
    } catch (error) {
      console.log(error);
      Alert.alert("Payment Error", "Failed to initialize payment");
    }
  };

  if (!booking) return <Text className="text-center mt-10">Loading...</Text>;

  return (
    <View className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-6">Payment</Text>
      <View className="bg-white p-4 rounded-2xl shadow mb-6">
        <Text className="text-gray-500 mb-1">Service</Text>
        <Text className="text-lg font-semibold mb-2">{booking.service_type}</Text>
        <Text className="text-gray-500 mb-1">Reference Code</Text>
        <Text className="text-gray-700 mb-2">{booking.reference_code}</Text>
        <Text className="text-gray-500 mb-1">Total Amount</Text>
        <Text className="text-gray-700 font-semibold">
          {booking.currency ?? "NGN"} {booking.total_price ?? "0.00"}
        </Text>
      </View>

      <PressableOpacity
        className={`bg-blue-600 py-3 rounded-xl ${paymentMutation.isPending ? "opacity-50" : ""}`}
        onPress={handlePayment}
        disabled={paymentMutation.isPending}
      >
        <Text className="text-white text-center font-semibold">
          {paymentMutation.isPending ? "Processing..." : "Pay Now"}
        </Text>
      </PressableOpacity>
    </View>
  );
}
