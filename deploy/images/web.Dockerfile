FROM node:24-bookworm-slim@sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205 AS builder
WORKDIR /app/apps/web
ARG API_INTERNAL_URL=http://mentor-api:8000/api
ENV API_INTERNAL_URL=${API_INTERNAL_URL} NEXT_TELEMETRY_DISABLED=1 NEXT_STANDALONE=1
COPY apps/web/package.json apps/web/package-lock.json ./
COPY .build/mentor/npm-cache/_cacache /deps/npm-cache/_cacache
RUN --network=none npm ci --offline --cache /deps/npm-cache --no-audit --no-fund
COPY apps/web/ ./
COPY scripts/collect-node-licenses.mjs scripts/check-web-build.mjs /tmp/
RUN npm run build && node /tmp/check-web-build.mjs \
    && node /tmp/collect-node-licenses.mjs

FROM node:24-bookworm-slim@sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205
ARG SOURCE_REVISION=working-tree
LABEL org.opencontainers.image.source="https://github.com/saasMsDGH/mentor" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3001 HOSTNAME=0.0.0.0 \
    API_INTERNAL_URL=http://mentor-api:8000/api
WORKDIR /app
RUN groupadd --gid 1001 mentor \
    && useradd --uid 1001 --gid 1001 --no-create-home --shell /usr/sbin/nologin mentor
COPY --from=builder --chown=1001:1001 /app/apps/web/.next/standalone ./
COPY --from=builder --chown=1001:1001 /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=1001:1001 /app/apps/web/public ./apps/web/public
COPY --from=builder /app/apps/web/THIRD_PARTY_LICENSES /usr/share/licenses/mentor/npm
COPY LICENSE /usr/share/licenses/mentor/LICENSE
USER 1001:1001
EXPOSE 3001
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:3001').then(r => {if (!r.ok) process.exit(1)}).catch(() => process.exit(1))"
CMD ["node", "apps/web/server.js"]
