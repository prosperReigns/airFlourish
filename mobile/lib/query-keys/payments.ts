export const paymentsQueryKeys = {
  all: ["payments"] as const,
  list: () => [...paymentsQueryKeys.all, "list"] as const,
};
