# flagstone-sdk

Python SDK for Flagstone feature flags.

The client downloads your project's flag configuration once and **evaluates flags locally**, in your
application's process. A flag check is a dictionary lookup and a few comparisons, with no network
call, so it is safe to use in hot paths. The client keeps its copy up to date in the background,
and keeps working with the last configuration it had if the Flagstone server is unreachable.

## Install

```bash
pip install flagstone-sdk
```

Requires Python 3.10 or newer. The only dependency is [httpx](https://www.python-httpx.org/).

## Quickstart

```python
from flagstone_sdk import FlagClient

client = FlagClient(
    sdk_key="fs_...",                      # from your project's "SDK keys" page
    base_url="https://flags.example.com",  # where your Flagstone server runs
)

user = {"id": "user-123", "plan": "pro", "country": "IN"}

if client.is_enabled("new-dashboard", user):
    show_new_dashboard()

# Record that this user converted, for the flag's experiment results.
client.track_conversion("new-dashboard", user)

client.close()  # on shutdown
```

Create one client when your application starts and share it. Creating a client fetches the
configuration and starts a background refresh thread.

## Users and targeting

A user is a plain `dict`. `"id"` is required: it decides which side of a percentage rollout the
user falls on, and the same id always gets the same answer. Any other keys (`plan`, `country`,
`email`, ...) are attributes that targeting rules can match on. Rules and rollouts are configured in
the Flagstone admin UI.

## API

| Method | Returns |
| --- | --- |
| `is_enabled(flag_key, user)` | `True` if the variation served to this user is truthy. Records an exposure event. Unknown flags return `False`. |
| `get_variation(flag_key, user)` | Index of the variation served to this user. Does not record an event. Unknown flags return `0`. |
| `track_conversion(flag_key, user)` | Records a conversion for the variation this user is served. |
| `close()` | Stops background refreshes and releases the HTTP connection. |

### Options

| Argument | Default | Meaning |
| --- | --- | --- |
| `sdk_key` | required | The project's SDK key. |
| `base_url` | `http://localhost:8000` | URL of your Flagstone server. |
| `poll_interval` | `30` | Seconds between configuration refreshes when polling. |
| `use_sse` | `False` | Receive changes over Server-Sent Events instead of polling. Changes arrive within a second, but the connection must be allowed through any proxies in between. |
| `cache_path` | `~/.flagstone_cache.json` | Where the last configuration is saved, so the client can start even if the server is down. `None` disables the cache. |
| `flush_interval` | `10` | Seconds between sending batched events. Events are also sent every 100 events. |

## Keep SDK keys on the server

The client downloads the full configuration of the key's project, including targeting rules and the
values they compare against. Use the SDK only in server-side code. Never put an SDK key in a browser,
mobile app or any code your users can read.

## Good to know

- Events are delivered on a best-effort basis: if sending a batch fails, that batch is dropped.
- `close()` does not send events that are still buffered; up to `flush_interval` seconds of events
  can be lost at shutdown.

## License

MIT. The full license text is included in the package.
