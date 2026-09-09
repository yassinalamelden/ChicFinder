# ChicFinder Mobile

The iOS and Android app for ChicFinder, built with Expo (React Native) on top of
the same FastAPI backend the web frontend uses.

## What's in it

| Screen | What it does |
|---|---|
| Search | Camera or photo library, uploads to `/api/v1/recommend`, shows matches |
| Stores | Egyptian brands from `/api/v1/stores`, public so it works before sign-in |
| Store detail | Brand header plus its catalog, filterable by category |
| Saved | Wishlist backed by `/api/v1/saved` |
| Profile | Account summary, privacy policy, support, sign out, delete account |
| Welcome | Sign in with Apple, Google, or email |

## Setup

Requires Node 18+ and the Expo CLI (bundled, run through `npx`).

```bash
cd mobile
npm install
cp .env.example .env     # then fill in the values
npm start
```

Scan the QR code with Expo Go on a phone, or press `i` for the iOS simulator on
a Mac.

> Sign in with Apple and Google sign-in need a development build rather than
> Expo Go, because both require native configuration tied to the bundle ID:
> `npx eas build --profile development --platform ios`. Email and password
> sign-in works in Expo Go.

### Pointing at a backend

`EXPO_PUBLIC_API_URL` defaults to `http://localhost:8000`, which a physical
phone cannot reach. On a device, use your computer's LAN address:

```bash
EXPO_PUBLIC_API_URL=http://192.168.1.20:8000 npm start
```

## Project layout

```
mobile/
  app/                     expo-router routes; the file tree is the navigation
    _layout.tsx            providers plus the signed-in/signed-out gate
    (auth)/welcome.tsx     sign-in
    (tabs)/                search, stores, saved, profile
    store/[storeId].tsx    store detail
    delete-account.tsx     account deletion (App Store Guideline 5.1.1(v))
  src/
    lib/api.ts             typed client for the FastAPI backend
    lib/firebase.ts        Firebase init with React Native persistence
    context/AuthContext    sign-in methods and session state
    context/SavedContext   wishlist state, optimistic toggles
    components/            ProductCard and shared UI
    theme.ts               design tokens shared with the web frontend
  scripts/generate_icons.py   regenerates the icon set
```

## Commands

```bash
npm start              # dev server
npm run typecheck      # tsc --noEmit
npm run ios            # dev server, opens the iOS simulator (Mac only)
npx expo export --platform ios   # verify the bundle builds without a Mac
```

## Building for the App Store

Builds run on Expo's macOS machines, so no Mac is needed locally.

```bash
npm install -g eas-cli
eas login
eas init                                    # writes the EAS project ID
eas build --platform ios --profile preview  # TestFlight-installable build
eas build --platform ios --profile production
eas submit --platform ios --profile production
```

Fill in `ascAppId` and `appleTeamId` in `eas.json` before the first submit.
Secrets go in EAS environment variables, not in a committed `.env`:

```bash
eas env:create --name EXPO_PUBLIC_FIREBASE_API_KEY --value "..." --environment production
```

The full submission process, including what Apple asks for and the common
rejection reasons, is in [docs/app-store-submission.md](../docs/app-store-submission.md).

## Backend endpoints this app depends on

| Method | Endpoint | Auth |
|---|---|---|
| POST | `/api/v1/recommend` | Firebase JWT |
| GET | `/api/v1/stores` | public |
| GET | `/api/v1/stores/{id}` | public |
| GET | `/api/v1/saved` | Firebase JWT |
| GET | `/api/v1/saved/ids` | Firebase JWT |
| PUT | `/api/v1/saved/{item_id}` | Firebase JWT |
| DELETE | `/api/v1/saved/{item_id}` | Firebase JWT |
| DELETE | `/api/v1/account` | Firebase JWT |

The saved-items table needs its migration applied once:

```bash
psql "$DATABASE_URL" -f ../scripts/migrations/001_saved_items.sql
```

## Testing locally without the real catalog

The production catalog lives in RDS and S3, so a fresh clone has no products to
render and the Stores and Saved screens look broken when they are only empty.
Generate throwaway sample data instead:

```bash
python3 scripts/generate_sample_catalog.py   # from the project root
```

That writes `stores.json`, `products.json` and placeholder images into
`data/raw_images/`, all of which are gitignored. Restart the API to pick them up.

What this does and does not unlock:

| Feature | Works with sample data |
|---|---|
| Stores tab, store detail, category filter | yes |
| Product cards, images, prices | yes |
| Saving and unsaving | needs a local Postgres and the migration above |
| Photo search | no, needs the real product images and a built FAISS index |

Photo search cannot be faked usefully: it needs the actual catalog images to
embed. Get those from the team rather than trying to work around it.
