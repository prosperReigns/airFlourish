import axios from "axios";
import { useRouter, useSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { Alert, Text, TouchableOpacity, View } from "react-native";

interface Booking {
  id: number;
  service_type: string;
  total_price: number;
  currency: string;
  reference_code: string;
}

export default function PaymentScreen() {
  const { bookingId } = useSearchParams();
  const router = useRouter();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    axios
      .get(`https://192.168.0.200:8000/api/bookings/${bookingId}/`)
      .then((res) => setBooking(res.data))
      .catch((err) => console.log(err));
  }, [bookingId]);

  const handlePayment = async () => {
    if (!booking) return;

    setLoading(true);

    // Generate a unique tx_ref
    const txRef = `TX-${booking.reference_code}`;

    try {
      // Initialize payment on backend (Flutterwave)
      const res = await axios.post(
        "https://your-backend.com/api/payments/init/",
        {
          amount: booking.total_price,
          currency: booking.currency,
          tx_ref: txRef,
        },
      );

      const { payment_link } = res.data;

      // Open payment link (Expo Linking)
      import("expo-linking").then(({ default: Linking }) => {
        Linking.openURL(payment_link);
      });
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
          {booking.currency} {booking.total_price}
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
