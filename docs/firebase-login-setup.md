# Optional sign-in (result history + email opt-in)

This adds a **completely optional** "Sign in with Google" button. It has no effect
on the anonymous validation study (`data-collection-setup.md`) — that pipeline
keeps working exactly as before, with or without this configured.

**What it's for:** someone can sign in to keep a private history of their own
results across retakes, viewable from "My results." At sign-in they can also
opt in to hear about future Genius Index releases — which is how this collects
email addresses, only from people who explicitly checked that box.

**What it's not:** it doesn't touch the anonymous pilot data in your Sheet, it
doesn't require anyone to sign in to take the assessment, and until you
configure it below, the sign-in button doesn't exist on the page at all — no
extra network requests, nothing loaded.

---

## One-time setup (~10 minutes)

### 1. Create a Firebase project
1. Go to <https://console.firebase.google.com> and **Add project** (the free
   "Spark" plan covers this easily — sign-in and this much Firestore usage cost
   nothing at this scale).
2. Name it anything, e.g. *Genius Index*.

### 2. Turn on Google sign-in
1. In the Firebase console: **Build → Authentication → Get started**.
2. Under **Sign-in method**, enable **Google**. Pick a support email (yours).

### 3. Turn on Firestore
1. **Build → Firestore Database → Create database**.
2. Start in **production mode** (we'll paste in real rules below — don't leave
   it in permissive test mode).
3. Pick any region close to you.

### 4. Add a Web app and copy its config
1. Project **Settings** (gear icon) → scroll to **Your apps** → click the
   **</>** (web) icon → register an app (any nickname, no need for Firebase
   Hosting).
2. It shows a `firebaseConfig` object like:
   ```js
   {
     apiKey: "AIza...",
     authDomain: "genius-index-xxxxx.firebaseapp.com",
     projectId: "genius-index-xxxxx",
     storageBucket: "genius-index-xxxxx.appspot.com",
     messagingSenderId: "...",
     appId: "..."
   }
   ```
   Copy the whole thing.

### 5. Paste it into the site
1. Open [`index.html`](./index.html), find near the top:
   ```js
   const FIREBASE_CONFIG = {};
   ```
2. Paste your config in:
   ```js
   const FIREBASE_CONFIG = {
     apiKey: "AIza...",
     authDomain: "genius-index-xxxxx.firebaseapp.com",
     projectId: "genius-index-xxxxx",
     storageBucket: "genius-index-xxxxx.appspot.com",
     messagingSenderId: "...",
     appId: "..."
   };
   ```
3. Commit and let the site redeploy.

> This config is not a secret — it's meant to be visible in client-side code
> (that's how every Firebase web app works). What actually protects the data
> is the Firestore security rules in step 7, not hiding this object.

### 6. Authorize your live domain
Google sign-in only works from domains Firebase knows about.
1. **Authentication → Settings → Authorized domains**.
2. `localhost` is there by default (for local testing). Add your Pages domain:
   `dixon8303.github.io`.

### 7. Lock down Firestore with security rules
1. **Firestore Database → Rules**, replace the contents with:
   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /users/{uid} {
         allow read, write: if request.auth != null && request.auth.uid == uid;
         match /results/{resultId} {
           allow read, write: if request.auth != null && request.auth.uid == uid;
         }
       }
     }
   }
   ```
2. **Publish**.

This means each signed-in person can only ever read or write their *own*
profile and their *own* results — never anyone else's, and never anonymously.

---

## What gets stored, and where

- `users/{uid}` — one document per signed-in person: `email`, `displayName`,
  `marketingOptIn` (true only if they checked the box at sign-in), `createdAt`.
- `users/{uid}/results/{resultId}` — one document per completed assessment
  taken while signed in: the same export object the anonymous pipeline sends,
  plus a server timestamp for sorting.

Nobody is written to Firestore unless they explicitly click "Sign in with
Google" — taking the assessment anonymously never touches this at all.

## Viewing/exporting the email list

For "email everyone who opted in to future releases": in the Firebase console,
**Firestore Database → Data → users**, or query
`users` where `marketingOptIn == true` from the console's query builder, and
export the `email` field. There's no built-in export button — for a mailing
list at scale, consider a small script using the Firebase Admin SDK, or just
copy addresses out of the console for now.

## Turning it off again

Set `FIREBASE_CONFIG` back to `{}` and redeploy. The sign-in button disappears,
no Firebase code loads, and already-stored profiles/results stay in Firestore
untouched (visible again if you turn it back on later).
