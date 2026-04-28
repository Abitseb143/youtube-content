# Faceless YT

Multi-tenant SaaS for AI-generated faceless YouTube channel automation.

See `docs/superpowers/specs/` for design and `docs/superpowers/plans/` for implementation plans.

## Local development (when Docker is available)

```bash
make dev      # Start postgres, redis, minio + watch all apps
make test     # Run all tests
make migrate  # Run Alembic migrations
```

## Deployment

This project deploys to Railway. See `docs/deployment/railway.md` (added in Railway-config phase).
