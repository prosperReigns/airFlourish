import { Pressable } from "react-native-gesture-handler";
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from "react-native-reanimated";
import type { PressableProps } from "react-native";

type AnimatedPressableProps = PressableProps & {
  className?: string;
};

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export function PressableOpacity({
  children,
  onPressIn,
  onPressOut,
  style,
  className,
  ...props
}: AnimatedPressableProps) {
  const progress = useSharedValue(0);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: 1 - progress.value * 0.45,
    transform: [{ scale: 1 - progress.value * 0.02 }],
  }));

  return (
    <AnimatedPressable
      {...(props as any)}
      className={className}
      onPressIn={(event) => {
        progress.value = withTiming(1, { duration: 110 });
        onPressIn?.(event);
      }}
      onPressOut={(event) => {
        progress.value = withTiming(0, { duration: 140 });
        onPressOut?.(event);
      }}
      style={[style, animatedStyle]}
    >
      {children}
    </AnimatedPressable>
  );
}
