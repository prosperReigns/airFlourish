import axios from "axios";
import { useRouter } from "expo-router";
import { useState } from "react";
import {
    FlatList,
    Text,
    TextInput,
    TouchableOpacity,
    View,
} from "react-native";

interface Hotel {
  hotel_id: string;
  hotel_name: string;
  price: number;
  city: string;
}

export default function HotelSearchScreen() {
  const [city, setCity] = useState("");
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [hotels, setHotels] = useState<Hotel[]>([]);
  const router = useRouter();

  const searchHotels = () => {
    axios
      .get(`https://192.168.0.200:8000/api/hotels/search/`, {
        params: { city, check_in: checkIn, check_out: checkOut, guests: 1 },
      })
      .then((res) => setHotels(res.data))
      .catch((err) => console.log(err));
  };

  const renderHotel = ({ item }: { item: Hotel }) => (
    <TouchableOpacity
      className="bg-white rounded-2xl p-4 mb-4 shadow"
      onPress={() => router.push(`/hotels/book/${item.hotel_id}`)}
    >
      <Text className="text-lg font-semibold">{item.hotel_name}</Text>
      <Text className="text-gray-500">{item.city}</Text>
      <Text className="text-gray-700 mt-1">NGN {item.price}</Text>
    </TouchableOpacity>
  );

  return (
    <View className="flex-1 bg-gray-50 px-6 pt-6">
      <Text className="text-2xl font-bold mb-4">Search Hotels</Text>
      <TextInput
        placeholder="City"
        value={city}
        onChangeText={setCity}
        className="bg-white p-3 rounded-xl mb-2"
      />
      <TextInput
        placeholder="Check In (YYYY-MM-DD)"
        value={checkIn}
        onChangeText={setCheckIn}
        className="bg-white p-3 rounded-xl mb-2"
      />
      <TextInput
        placeholder="Check Out (YYYY-MM-DD)"
        value={checkOut}
        onChangeText={setCheckOut}
        className="bg-white p-3 rounded-xl mb-4"
      />
      <TouchableOpacity
        className="bg-blue-600 py-3 rounded-xl mb-6"
        onPress={searchHotels}
      >
        <Text className="text-white text-center font-semibold">Search</Text>
      </TouchableOpacity>

      <FlatList
        data={hotels}
        keyExtractor={(item) => item.hotel_id}
        renderItem={renderHotel}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}
