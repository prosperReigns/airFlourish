import { useMutation } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";

export const useLoginMutation = () => {
  const login = useAuth((state) => state.login);

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      login(email, password),
  });
};
