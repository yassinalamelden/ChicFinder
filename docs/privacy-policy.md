# ChicFinder Privacy Policy

**Draft. Not legal advice.** This covers what the app and backend as written
actually do. Before publishing it, check each section against your deployed
system, replace every `[bracketed]` placeholder, and have someone qualified
review it against Egyptian data protection law (Law No. 151 of 2020) and, if you
have users in the EU, the GDPR.

Apple requires a publicly reachable privacy policy URL for every app on the App
Store, so this needs to be live at a stable address before submission.

**Last updated:** [DATE]

---

## Who we are

ChicFinder is a fashion visual search service operated by [LEGAL ENTITY OR YOUR
NAME], [ADDRESS]. Questions about this policy or your data go to
[support@chicfinder.app].

## What we collect

**Account information.** When you create an account we receive your email
address and a unique user ID from our authentication provider, Google Firebase.
If you sign in with Apple and choose to hide your email, we receive Apple's
relay address instead of your real one, and that is all we ever see. If you sign
in with Apple or Google we may also receive the display name you have set there.

We never receive or store your password. Authentication is handled entirely by
Firebase.

**Photos you search with.** When you search, the photo you take or select is
uploaded to our servers, analysed to identify the clothing in it, and used to
find visually similar products. [State the retention here: either "The photo is
processed and discarded, and is not stored against your account", or "The photo
is stored for N days to improve search quality." Say whichever is true of your
deployment. The backend currently writes uploads to disk, so if that is still
the case, the second wording applies.]

**Saved items.** If you save an item, we store your user ID and the item's ID so
your wishlist follows you between devices.

**Technical information.** Our servers log ordinary request data such as IP
address, timestamp and the endpoint called, which we use to keep the service
running and to investigate faults.

## What we do not collect

We do not collect your location, contacts, calendar, health data, or advertising
identifiers. We do not track you across other apps or websites. We do not show
advertising.

## How we use it

- To run visual search and return product matches
- To keep you signed in and to hold your saved items
- To keep the service secure, available and working
- To respond when you contact support

We do not sell your personal data, and we do not share it with advertisers.

## Who we share it with

We use these providers, and only for the purposes above:

| Provider | What it handles |
|---|---|
| Google Firebase | Authentication and account identity |
| Amazon Web Services | Hosting, databases and file storage |
| OpenRouter, and through it Google's Gemini models | Analysing search photos to identify clothing |

When you search, the photo is sent to our model provider for analysis. We do not
send your name, email or user ID with it.

We may also disclose information where the law requires it.

## Where your data is held

Our infrastructure runs in [AWS eu-central-1, Frankfurt, Germany]. Using the app
from Egypt or elsewhere means your data is transferred to and processed in that
region.

## How long we keep it

Account data and saved items are kept until you delete your account. Server logs
are kept for [N days]. [Photo retention, matching what you stated above.]

## Your choices

**Delete your account.** Open the Profile tab, tap Delete account, and confirm.
This permanently removes your account, your saved items and the data we hold for
you. It cannot be undone.

**Camera and photo access.** The app asks only when you tap Camera or Photos,
and you can withdraw permission at any time in the iOS Settings app. Search will
not work without it, but the rest of the app still does.

**Access, correction and objection.** Email [support@chicfinder.app] to ask what
we hold about you, to correct it, or to object to how we use it. We reply within
30 days.

## Children

ChicFinder is not directed at children under 13, and we do not knowingly collect
their data. If you believe a child has created an account, contact us and we
will delete it.

## Security

Traffic between the app and our servers uses HTTPS. Data at rest is encrypted by
our hosting provider. Access to production systems is limited to people who need
it. No system is perfectly secure, so we cannot guarantee absolute security.

## Changes

If we change this policy we will update the date above and, for material
changes, tell you in the app.

## Contact

[support@chicfinder.app]
[LEGAL ENTITY OR YOUR NAME]
[ADDRESS]
