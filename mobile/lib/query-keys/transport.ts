export const transportQueryKeys = {
  all: ["transport"] as const,
  options: () => [...transportQueryKeys.all, "options"] as const,
};
