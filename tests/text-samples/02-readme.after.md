# ConfigManager

Multi-environment configuration management for Node.js applications. Handles
config loading, validation, and hot reload.

## Features

- Auto-detects environment (dev/staging/prod) and loads the right config
- Schema-based validation (catches bad config at startup, not at 3am)
- Reads from YAML files, env vars, and remote sources (Consul, etcd)
- Type-safe accessors -- `config.get<number>('port')` won't return a string
- Hot reload without restart

## Quick start

```bash
npm install configmanager
```

Create a schema file defining your config structure:

```yaml
# config.schema.yml
port:
  type: integer
  default: 3000
  env: APP_PORT
database_url:
  type: string
  required: true
  env: DATABASE_URL
```

Then in your app:

```typescript
import { loadConfig } from 'configmanager';

const config = await loadConfig('./config.schema.yml');
const port = config.get<number>('port'); // 3000
```

## Why this exists

Managing config across environments is annoying. Env vars get out of sync,
YAML files drift between environments, and type mismatches surface in production
instead of at deploy time. ConfigManager validates everything at startup against
a schema so you catch problems early.

## Contributing

PRs welcome. See `CONTRIBUTING.md` for guidelines.
