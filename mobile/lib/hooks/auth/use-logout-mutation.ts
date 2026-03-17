import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";

export const useLogoutMutation = () => {
  const logout = useAuth((state) => state.logout);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logout,
    onSuccess: async () => {
      await queryClient.clear();
    },
  });
};
