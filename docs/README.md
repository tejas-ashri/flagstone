# Flagstone documentation

These documents explain how Flagstone is built and why. For setup and day-to-day commands, see the [project README](../README.md).

| Document | Read it to learn |
| --- | --- |
| [Architecture](architecture.md) | The components, how they connect, the data model, and how a request travels through the system |
| [How it works](how-it-works.md) | The life of a flag: evaluation, rollout bucketing, the SDK's refresh and caching, events and experiment results |
| [Backend services](backend-services.md) | Every module under `backend/`, with its role, its key functions and why it matters |
| [Authentication and access control](authentication.md) | Sign-in with GitHub, Google and Slack, sessions, roles, SDK keys and project isolation |
| [Frontend](frontend.md) | The admin UI's routes, state, and how it talks to the API |
| [Design decisions](design-decisions.md) | The trade-offs behind the main choices, and the known limitations |

## Suggested reading order

New to the codebase: **Architecture → How it works → Backend services**. Read the other three as needed.

## Glossary

| Term | Meaning |
| --- | --- |
| **Flag** | A named switch (`key`) with a list of possible values (*variations*), targeting rules, an optional percentage rollout and a default. |
| **Variation** | One possible value a flag returns. Variations are referred to by index; `[false, true]` is the common boolean case. |
| **Rule** | "If user attribute X *operator* Y, serve variation N." Rules are checked in order and the first match wins. |
| **Rollout** | "Serve variation N to P% of users who matched no rule." Users are bucketed deterministically by their `id`. |
| **Project** | The unit of isolation. Flags, events, SDK keys and members all belong to one project. |
| **SDK key** | The credential an application uses. It is tied to one project and can only read and report on that project's flags. |
| **Exposure** | An event recorded when the SDK evaluates a flag for a user with `is_enabled`. |
| **Conversion** | An event your application records with `track_conversion` when a user reaches the goal being measured. |
| **Default project** | The project that holds data from before projects existed, and that the original `/api/flags` paths act on. |
