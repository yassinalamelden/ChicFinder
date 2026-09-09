# Shipping ChicFinder to the App Store

Everything between "the code is written" and "the app is live." Work through it
top to bottom. The gating items are marked **blocker**, because they stop a
submission dead rather than just slowing it down.

Apple changes its rules and its tooling regularly. Every claim here links to
Apple's own page, and those pages are the authority if they disagree with this
document.

---

## 1. Enrol in the Apple Developer Program

**Blocker. Start this first, because it is the only step with a queue you do not
control.**

- Cost: 99 USD per year, renewed annually.
  ([Apple Developer Program](https://developer.apple.com/programs/))
- Enrol at [developer.apple.com/programs/enroll](https://developer.apple.com/programs/enroll/).
- Individual enrolment verifies your identity with a government ID. It usually
  clears in a couple of days, occasionally longer.
- Organization enrolment (publishing as a registered company) additionally needs
  a D-U-N-S number for the entity, which is free but can take up to two weeks to
  issue. ([Apple's D-U-N-S guidance](https://developer.apple.com/support/D-U-N-S/))

**Which one?** Individual is faster and fine to start with. The seller name on
the App Store is then your own legal name rather than a brand, and moving an app
from an individual account to a company account later is possible but is a
support request, not a button. If ChicFinder already has a registered entity,
enrol as the organization now and skip that migration.

Egypt is a supported region for both enrolment and paid App Store agreements.

---

## 2. Prerequisites checklist

| Item | Status | Notes |
|---|---|---|
| Apple Developer Program membership | needed | Section 1 |
| Bundle ID `app.chicfinder.mobile` registered | needed | EAS registers it automatically on first build |
| App record created in App Store Connect | needed | [appstoreconnect.apple.com](https://appstoreconnect.apple.com) |
| Backend reachable over HTTPS from the public internet | **blocker** | See section 3 |
| Privacy policy live at a public URL | **blocker** | Draft at [docs/privacy-policy.md](privacy-policy.md) |
| Support URL or support email | **blocker** | Apple requires a working contact |
| App icon, 1024x1024, no alpha | done | `mobile/assets/icon.png` |
| Screenshots for a 6.9" iPhone | needed | Section 6 |
| Demo account for the review team | **blocker** | Section 7 |
| Sign in with Apple implemented | done | `src/context/AuthContext.tsx` |
| In-app account deletion | done | `app/delete-account.tsx` |

---

## 3. Backend readiness

The reviewer runs the app against your production backend. If it is down or
unreachable, the app is rejected under
[Guideline 2.1 App Completeness](https://developer.apple.com/app-store/review/guidelines/#app-completeness).

- [ ] API served over **HTTPS with a valid certificate**. Apple's App Transport
      Security blocks plain HTTP by default, and asking for an exception invites
      questions during review.
      ([App Transport Security](https://developer.apple.com/documentation/security/preventing-insecure-network-connections))
- [ ] A real domain in front of the ECS service, for example
      `api.chicfinder.app`, rather than a load balancer hostname.
      This is already tracked as follow-up C2 in the AWS migration spec.
- [ ] `APP_ENV=production` set, so `get_current_user` fails closed instead of
      falling back to the dev stub. Verify by calling `/api/v1/saved` with no
      token and confirming a 401.
- [ ] Saved-items migration applied:
      `psql "$DATABASE_URL" -f scripts/migrations/001_saved_items.sql`
- [ ] Firebase Admin credentials present in the task definition, otherwise
      account deletion cannot remove the auth record and returns 502.
- [ ] The FAISS index is built and mounted, so `/recommend` returns real
      results. An empty result set on every search reads as a broken app.

---

## 4. Firebase and Google configuration

- [ ] Add an **iOS app** to the existing Firebase project with bundle ID
      `app.chicfinder.mobile`. Copy the config values into the
      `EXPO_PUBLIC_FIREBASE_*` variables.
- [ ] Enable **Apple** as a sign-in provider in Firebase Authentication.
      Firebase's setup page lists the Service ID and key it needs.
      ([Firebase: Apple sign-in](https://firebase.google.com/docs/auth/ios/apple))
- [ ] In the Apple Developer portal, enable the **Sign in with Apple**
      capability for the App ID.
- [ ] Create OAuth client IDs (iOS, Android, Web) in Google Cloud and set the
      `EXPO_PUBLIC_GOOGLE_*` variables. The iOS client's bundle ID must match
      exactly.
- [ ] Add the production API domain to Firebase's authorised domains.

---

## 5. Build and distribute

```bash
cd mobile
npm install -g eas-cli
eas login
eas init                 # creates the EAS project, writes the project ID
eas build --platform ios --profile preview
```

The preview build installs through TestFlight for internal testing. Once it
behaves, cut the production build and submit:

```bash
eas build --platform ios --profile production
eas submit --platform ios --profile production
```

Set `ascAppId` and `appleTeamId` in `mobile/eas.json` first. Both appear in App
Store Connect once the app record exists.
([Expo: submitting to the App Store](https://docs.expo.dev/submit/ios/))

Secrets belong in EAS environment variables rather than a committed `.env`:

```bash
eas env:create --name EXPO_PUBLIC_FIREBASE_API_KEY --value "..." --environment production
```

---

## 6. Store listing assets

**Screenshots.** Apple requires at least one set sized for a 6.9-inch iPhone
display; other sizes are scaled from it. Capture them from the simulator on the
matching device.
([Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications/))

Five worth taking, in this order:

1. The search screen with the camera prompt
2. A results grid full of matches
3. A store detail page
4. The saved tab with a few items
5. The sign-in screen

**Text.** Prepared drafts:

- **Name (30 chars max):** `ChicFinder`
- **Subtitle (30 chars max):** `Snap an outfit, shop Egypt`
- **Keywords (100 chars, comma separated, no spaces):**
  `fashion,outfit,visual search,egypt,shopping,style,clothes,brands,photo search,wishlist`
- **Promotional text (170 chars):**
  `Photograph any outfit and ChicFinder finds visually similar pieces from Egyptian brands, with prices and links to buy.`
- **Description:** see the draft at the end of this document.
- **Category:** Shopping (primary), Lifestyle (secondary)
- **Age rating:** answer the questionnaire honestly. With no user-generated
  content, no ads and no restricted material, ChicFinder should land at 4+.

---

## 7. Demo account for App Review

**Blocker.** The app requires sign-in, so Apple requires working credentials in
the App Review Information field. A reviewer who cannot get in rejects under
[Guideline 2.1](https://developer.apple.com/app-store/review/guidelines/#app-completeness).

- [ ] Create a real Firebase account, for example `appreview@chicfinder.app`,
      with a fixed password.
- [ ] Seed it with three or four saved items so the Saved tab is not empty.
- [ ] Confirm it can sign in against **production**, not just locally.
- [ ] Put the credentials in App Store Connect under App Review Information.
- [ ] Add a note pointing the reviewer at deletion, which they check explicitly:

> Account deletion: sign in, open the Profile tab, tap Delete account, type
> DELETE and confirm. This permanently removes the account and all saved items.

Do not delete this account between review rounds.

---

## 8. Privacy and compliance

- [ ] **App Privacy details.** App Store Connect asks what data the app collects
      and how it is used. For ChicFinder as built: email address and user ID,
      linked to the user's identity, used for app functionality; photos, used
      for app functionality and not linked to identity, since a search photo is
      processed and not stored against the account.
      ([App privacy details](https://developer.apple.com/app-store/app-privacy-details/))
      Answer this against what the backend actually does. If search photos are
      retained in the `uploads/` directory, they are stored data and must be
      disclosed as such, or the retention should be removed first.
- [ ] **Privacy policy URL.** Required for every app.
      Publish [docs/privacy-policy.md](privacy-policy.md) somewhere public and
      set `EXPO_PUBLIC_PRIVACY_POLICY_URL` to it.
- [ ] **Encryption export compliance.** Already declared in `app.config.ts` as
      `usesNonExemptEncryption: false`, which is correct for an app using only
      standard HTTPS.
      ([Export compliance](https://developer.apple.com/documentation/security/complying-with-encryption-export-regulations))
- [ ] **Third-party content.** The catalog shows brand names, product images and
      prices from Egyptian retailers. Have written permission from each brand,
      or use only material they publish for resellers. Apple rejects apps that
      display another company's content without rights under
      [Guideline 5.2](https://developer.apple.com/app-store/review/guidelines/#intellectual-property),
      and a brand complaint after launch is worse than a rejection before it.

---

## 9. The rules most likely to bite

| Guideline | What it says | Where ChicFinder stands |
|---|---|---|
| [4.8 Login Services](https://developer.apple.com/app-store/review/guidelines/#login-services) | An app offering a third-party login must also offer a login option that limits data collection to name and email and lets the user keep their email private. Sign in with Apple qualifies. | Implemented, listed first on iOS |
| [5.1.1(v) Account deletion](https://developer.apple.com/support/app-account-deletion/) | An app that lets users create an account must let them delete it from inside the app. Deactivation is not enough. | Implemented, deletes data then the auth record |
| [2.1 App Completeness](https://developer.apple.com/app-store/review/guidelines/#app-completeness) | No placeholder content, no broken features, working demo credentials. | Depends on section 3 and 7 |
| [4.2 Minimum Functionality](https://developer.apple.com/app-store/review/guidelines/#minimum-functionality) | An app must do more than repackage a website. | Native camera, native navigation, native auth. Fine. |
| [5.1.1 Data collection](https://developer.apple.com/app-store/review/guidelines/#data-collection-and-storage) | Ask for permission only in context, and explain why. | Camera and photo prompts fire on tap, with specific strings |
| [3.1.1 In-App Purchase](https://developer.apple.com/app-store/review/guidelines/#in-app-purchase) | Digital goods must use IAP. Physical goods must not. | Clothing is physical, so linking out to brands is allowed |

---

## 10. Submitting

1. Upload the production build (`eas submit` does this).
2. In App Store Connect, attach the build to the version.
3. Fill in listing text, screenshots, age rating, App Privacy, and App Review
   Information including the demo account.
4. Submit for review.

Review commonly takes a day or two. A rejection arrives as a message in App
Store Connect's Resolution Center; most are one specific fix followed by a
resubmission, not a verdict on the app.

After approval, choose whether to release immediately or hold it for a manual
release date.

---

## 11. After launch

- Crash reports appear in App Store Connect and in EAS.
- Ship JS-only fixes over the air with `eas update`, which skips review for
  changes that do not alter native code.
  ([Expo Updates](https://docs.expo.dev/eas-update/introduction/))
- Anything touching native modules, permissions or the app icon needs a new
  build and a new review.

---

## Appendix: description draft

> Find the outfit. Shop the brand.
>
> ChicFinder turns any outfit photo into a shopping list. Photograph a look you
> like, or pick a picture from your camera roll, and ChicFinder matches it
> against thousands of real products from Egyptian fashion brands.
>
> HOW IT WORKS
> Snap or upload an outfit photo. ChicFinder reads the individual pieces in the
> image, finds visually similar items in its catalog, and shows you what to buy
> and where.
>
> BROWSE LOCAL BRANDS
> Explore the full catalog of participating Egyptian stores, filter by category,
> and open any product straight at the brand.
>
> SAVE WHAT YOU LOVE
> Keep pieces in your wishlist and come back to them whenever you like.
>
> BUILT FOR EGYPT
> Prices in Egyptian pounds, from brands that ship here.

---

## Sources

- [Apple Developer Program enrolment](https://developer.apple.com/programs/enroll/)
- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Offering account deletion in your app](https://developer.apple.com/support/app-account-deletion/)
- [Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications/)
- [App privacy details on the App Store](https://developer.apple.com/app-store/app-privacy-details/)
- [Complying with encryption export regulations](https://developer.apple.com/documentation/security/complying-with-encryption-export-regulations)
- [Expo: build and submit to the App Store](https://docs.expo.dev/submit/ios/)
- [Firebase: authenticate with Apple](https://firebase.google.com/docs/auth/ios/apple)
