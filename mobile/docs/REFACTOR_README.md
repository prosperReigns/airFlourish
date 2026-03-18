# React Native Structure Refactor Notes

## What changed
- Shifted auth state management from a `store`-first pattern to a hook-first pattern with `hooks/use-auth.ts`.
- Added `lib/` architecture inspired by `lifeline/`:
  - `lib/api/*` for API request modules.
  - `lib/hooks/*` for React Query hooks and auth mutations.
  - `lib/query-keys/*` for route-oriented query key organization.
- Introduced `components/providers/query-provider.tsx` and wrapped the app with `QueryProvider` in `app/_layout.tsx`.
- Migrated core flows to React Query-driven hooks:
  - login/register mutations
  - bookings list/detail queries
  - payment initiation mutation
- Moved route UI logic from `app/` into screen components under `components/screens/*`.

## Login flow updates
- Login now uses `useLoginMutation` and the shared `useAuth` hook.
- Register now uses `useRegisterMutation`.
- Tabs logout now uses `useLogoutMutation` and clears query cache.

## Compatibility layer
- Existing `services/*` modules were converted to thin re-exports of `lib/api/*` to keep older screens functional while migrating incrementally.
- `store/authStore.ts` now re-exports `useAuth` as a temporary compatibility alias.

## Remaining migration work
- Migrate remaining route screens (flights/hotels/visa/transport/profile/settings) to `components/screens/*` and `lib/hooks/*` query/mutation modules.
- Remove compatibility aliases once all imports are updated.

## Press interactions update
- Replaced `TouchableOpacity` usage in app and screen components with animated `PressableOpacity`.
- Added `components/ui/pressable-opacity.tsx` built with `react-native-gesture-handler` + `react-native-reanimated` so press animations run smoothly on the UI thread.

## Route/screens separation progress
- Continued the migration so route files under `app/` now primarily re-export screen components from `components/screens/*`.
- Added screen modules for tabs, flights, hotels, transport, visa, and bookings legacy route variants, keeping route files thin and focused on routing only.

## Full structure adoption update
- Migrated remaining screen-level data access away from `services/*` and `store/*` usage to `lib/api/*` + `lib/hooks/*`.
- Tabs/bookings/payments/profile and flights/hotels/transport/visa screens now consume dedicated query/mutation hooks under `lib/hooks/*`.
- Added domain API modules and query keys for flights, hotels, transport, and visa to match the lifeline-style architecture.
