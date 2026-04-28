FROM node:20-slim AS base
ENV NEXT_TELEMETRY_DISABLED=1
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
WORKDIR /app

# ---- deps stage ----
FROM base AS deps
COPY pnpm-workspace.yaml package.json ./
COPY apps/web/package.json ./apps/web/
COPY packages/shared-types/package.json ./packages/shared-types/
# Lockfile may not exist on first deploy; allow no-frozen for bootstrap.
COPY pnpm-lock.yaml* ./
RUN pnpm install --filter "@faceless-yt/web..." || pnpm install --filter "@faceless-yt/web..." --no-frozen-lockfile

# ---- build stage ----
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules
COPY pnpm-workspace.yaml package.json ./
COPY packages/shared-types ./packages/shared-types
COPY apps/web ./apps/web

# Build-time public env vars (Next bakes NEXT_PUBLIC_* into the bundle)
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_dummy_for_build
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
RUN cd apps/web && pnpm build

# ---- runtime stage ----
FROM base AS runner
ENV NODE_ENV=production
COPY --from=builder /app /app
EXPOSE 3000
WORKDIR /app/apps/web
CMD ["pnpm", "start"]
