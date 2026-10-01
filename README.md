# SkyKings Playtime API

The SkyKings Playtime API stores and retrieves player playtime records. It is a
Python application built with FastAPI and deployed as a Cloudflare Worker with
a Cloudflare D1 database.

## Features

- Per-user API key authentication
- Upload and retrieval of playtime entries
- System-authenticated administration endpoints
- Cloudflare D1 persistence
- Per-user rate limiting on user-facing endpoints
- FastAPI-generated API documentation

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js and npm
- A Cloudflare account with access to Workers and D1

## Project structure

## Local setup

Use `pywrangler` with `uv`:

```bash
uvx --from workers-py pywrangler sync
```

The Worker expects a `SYSTEM_API_KEY` runtime variable for administrative endpoints. You can add one in `wrangler.jsonc`.

Start the local Worker:

```bash
npm run dev
```

The local D1 database is managed by Wrangler. The API documentation is
available at the root URL (`/`) while the Worker is running.

## Deployment

Authenticate Wrangler with Cloudflare, then deploy the Worker:

```bash
npx wrangler login
npm run deploy
```

Configure `SYSTEM_API_KEY` as a Cloudflare Worker secret rather than committing
it to the repository:

```bash
npx wrangler secret put SYSTEM_API_KEY
```

The D1 database binding is named `PLAYTIME` and is configured in
`wrangler.jsonc`. The first deployment should initialize its tables by calling
`GET /init-db` with the system authorization key.

## Authentication

User endpoints use the `Authorization` header as an API key:

```http
Authorization: <user-api-key>
```

Administrative endpoints use the same header, but require the configured
`SYSTEM_API_KEY`.

## API endpoints

### User endpoints

| Method | Path | Description | Authentication |
| --- | --- | --- | --- |
| `GET` | `/@me` | Return the authenticated user ID | User API key |
| `GET` | `/@me/playtime` | Return all playtime entries for the authenticated user | User API key |
| `POST` | `/@me/playtime` | Add playtime entries for the authenticated user | User API key |

User endpoints are rate limited to five requests per five minutes per user.

### System endpoints

These endpoints are intended for trusted administrative tooling and are not
included in the public OpenAPI schema.

| Method | Path | Description | Authentication |
| --- | --- | --- | --- |
| `GET` | `/init-db` | Create the `api_keys` and `playtime` tables if they do not exist | System API key |
| `POST` | `/{user_id}/keys` | Replace and return the API key for a user | System API key |
| `GET` | `/{user_id}/playtime` | Return all playtime entries for a user | System API key |

`POST /{user_id}/keys` returns the newly generated key once. Store it
securely; generating another key for the same user invalidates the previous
key.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE.md) file for details.