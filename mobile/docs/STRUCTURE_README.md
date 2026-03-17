# Target Structure and Commit Titles

## Commit title used
1. `refactor: align mobile architecture with lifeline-style hooks/providers/query structure`

## New structure (high level)
- `app/` -> route handlers only (progressively migrated)
- `components/`
  - `providers/query-provider.tsx`
  - `screens/auth/*`
  - `screens/bookings/*`
  - `screens/flights/*`
  - `screens/hotels/*`
  - `screens/payments/*`
  - `screens/tabs/*`
  - `screens/transport/*`
  - `screens/visa/*`
- `hooks/`
  - `use-auth.ts`
- `lib/`
  - `api/*`
  - `hooks/auth/*`
  - `hooks/bookings/*`
  - `hooks/payments/*`
  - `query-keys/*`

## Query key naming strategy
- Keys are grouped by route/domain (`auth`, `bookings`, `payments`) and then split into `list/detail` or resource-specific leaves.

## Why this mirrors lifeline
- Business logic in hooks, not in route files.
- Providers separated from context/store concerns.
- API calls centralized in `lib/api`.
- Query lifecycle handled with TanStack Query hooks.


## Migration rule now in effect
- No `services/` or `store/` imports in app/component code; use `lib/api/*`, `lib/hooks/*`, and query keys instead.
