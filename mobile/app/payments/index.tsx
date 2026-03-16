import { Booking, getBooking } from "@/services/booking";
import { createIdempotencyKey, initiateCardPayment } from "@/services/payment";
import * as Linking from "expo-linking";
import { useSearchParams } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { Alert, Text, TouchableOpacity, View } from "react-native";

export default function PaymentScreen() {
  const { bookingId } = useSearchParams();
  const bookingIdValue = useMemo(
    () => (Array.isArray(bookingId) ? bookingId[0] : bookingId),
    [bookingId],
  );
  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!bookingIdValue) return;
    getBooking(bookingIdValue)
      .then((data) => setBooking(data))
      .catch((err) => console.log(err));
  }, [bookingIdValue]);

  const handlePayment = async () => {
    if (!booking) return;

    setLoading(true);

    // Generate a unique tx_ref
    const txRef = `PAY-${booking.reference_code}-${Date.now()}`;
    const currency = booking.currency ?? "NGN";

    try {
      // Initialize payment on backend (Flutterwave)
      const res = await initiateCardPayment({
        bookingId: booking.id,
        amount: booking.total_price,
        currency,
        txRef,
        idempotencyKey: createIdempotencyKey(),
      });

      const paymentLink = res.gateway?.link;
      if (!paymentLink) {
        throw new Error("Payment link missing");
      }

      // Open payment link (Expo Linking)
      await Linking.openURL(paymentLink);
    } catch (error) {
      console.log(error);
      Alert.alert("Payment Error", "Failed to initialize payment");
    } finally {
      setLoading(false);
    }
  };

  if (!booking) return <Text className="text-center mt-10">Loading...</Text>;

  return (
    <View className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-6">Payment</Text>

      <View className="bg-white p-4 rounded-2xl shadow mb-6">
        <Text className="text-gray-500 mb-1">Service</Text>
        <Text className="text-lg font-semibold mb-2">
          {booking.service_type}
        </Text>

        <Text className="text-gray-500 mb-1">Reference Code</Text>
        <Text className="text-gray-700 mb-2">{booking.reference_code}</Text>

        <Text className="text-gray-500 mb-1">Total Amount</Text>
        <Text className="text-gray-700 font-semibold">
          {booking.currency ?? "NGN"} {booking.total_price ?? "0.00"}
        </Text>
      </View>

      <TouchableOpacity
        className={`bg-blue-600 py-3 rounded-xl ${loading ? "opacity-50" : ""}`}
        onPress={handlePayment}
        disabled={loading}
      >
        <Text className="text-white text-center font-semibold">
          {loading ? "Processing..." : "Pay Now"}
        </Text>
      </TouchableOpacity>
    </View>
  );
}
