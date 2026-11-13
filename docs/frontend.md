# Frontend

The admin UI is a React 18 + TypeScript single-page app in `frontend/`, built with Vite and routed with React Router 6.

## Routes

| Path | Page | Notes |
| --- | --- | --- |
| `/login` | `LoginPage` | Buttons for each configured provider, plus dev sign-in when enabled. Shows sign-in errors passed back as `?error=` |
| `/projects` | `ProjectsPage` | Your projects with role and counts; create a project |
| `/profile` | `ProfilePage` | Account, linked sign-in methods, projects, sign out |
| `/projects/:projectId/flags` | `FlagsListPage` | Search and filter (kept in the URL), on/off toggles |
| `/projects/:projectId/flags/:flagKey` | `FlagEditor` | Variations, rules (drag to reorder), rollout, default |
| `…/flags/:flagKey/test` | `FlagTestPage` | Enter user attributes, see the variation and the reason |
| `…/flags/:flagKey/results` | `ExperimentResults` | Per-variation exposures, conversions, rate, lift; auto-refresh |
| `…/flags/:flagKey/sdk` | `FlagSdkPage` | A Python snippet for this flag |
| `/projects/:projectId/keys` | `KeysPage` | Create (shown once), list, revoke SDK keys |
| `/projects/:projectId/members` | `MembersPage` | Invite, change roles, remove; pending invitations |
| `/projects/:projectId/settings` | `SettingsPage` | Rename; delete (type the name to confirm) |

Every page is a real URL, so tabs, filters and flags can be bookmarked and shared.

## Structure

```
src/
├── main.tsx, router.tsx    entry point and route table
├── api/                    one function per backend endpoint
│   └── http.ts             fetch wrapper: errors, CSRF header, 401 handling
├── auth/                   AuthProvider (who is signed in), RequireAuth (route guard)
├── project/context.ts      current project + isAdmin, URL helpers
├── flag/context.ts         current flag, shared by the flag tabs
├── layouts/                Root (providers), AppLayout (top bar), ProjectLayout (side nav), FlagLayout (header + tabs)
├── pages/                  one component per route
├── components/             Modal/ConfirmDialog, toasts, Toggle, FlagEditor, ProviderLogo…
├── lib/
│   ├── draft.ts            editable flag state ↔ API payload, with validation
│   ├── values.ts           how JSON values are typed in as text and shown back
│   ├── useLoad.ts          fetch-on-mount hook that ignores stale responses
│   └── useFlagToggle.ts    optimistic on/off with rollback and Undo
└── types/                  TypeScript mirrors of the backend schemas
```

## State

There's no global store. State lives in three React contexts, each owned by a layout:

- **`AuthContext`** (from `/api/me`): the user and their projects with roles. Refreshed after anything that changes membership.
- **`ProjectContext`**: the current project and `isAdmin`, derived from `AuthContext` and the `:projectId` in the URL.
- **`FlagContext`**: the loaded flag, shared by its four tabs so a save on one is visible on the others.

Page data, such as the flag list, keys or members, is fetched by each page with `useLoad`.

## Talking to the API

`api/http.ts` wraps `fetch` and does four things for every call:
1. Adds `X-Requested-With: flagstone`, which the backend requires on writes (CSRF protection).
2. Sends the session cookie (`credentials: "same-origin"`).
3. Turns FastAPI error bodies, both `{"detail": "…"}` and validation lists, into readable messages.
4. On any **401**, tells `AuthProvider` that the session ended, and the route guard redirects to `/login?next=…`.

Flag keys and project ids are always passed through `encodeURIComponent` when building paths.

## Interaction details

- **Optimistic toggles.** The switch flips immediately; the API call follows; failure reverts it with an error toast, and success offers **Undo**.
- **Unsaved changes.** The editor compares a fingerprint of the draft to the saved flag. Leaving with edits (another tab, another flag, any link) opens a confirmation via React Router's `useBlocker`; closing the browser tab triggers the browser's own warning.
- **Validation before saving.** `lib/draft.ts` rejects what the backend would accept but the SDK would crash on: out-of-range variation indexes, rollout percentages outside 0–100, duplicate variations, and non-numeric values for `gt`/`lt`.
- **Typed values.** Variation and rule values are typed as text; anything that parses as JSON (`true`, `42`, `{"a":1}`) is stored as that value, otherwise it's a string. Strings that would be misread, like the string `"true"`, are shown quoted, so editing round-trips exactly.
- **Viewer mode.** For viewers the editor is wrapped in a disabled `<fieldset>`, which makes every control read-only, and admin-only buttons are hidden.
- **Dialogs** use the native `<dialog>` element, which gives focus trapping, Esc to close and a backdrop. Destructive actions on flags and projects ask you to type the name.

## Development

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, proxies /api, /auth, /sdk to :8000
npm run build    # type-check + production build into dist/
npm run lint
```
