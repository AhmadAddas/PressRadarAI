FROM node:24.20.0-alpine AS dependencies

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY src ./src

FROM dependencies AS development

FROM node:24.20.0-alpine AS production

WORKDIR /app
RUN apk upgrade --no-cache
COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=dependencies /app/src ./src

RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack && \
    rm -f /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack /usr/local/bin/yarn /usr/local/bin/yarnpkg

USER node
EXPOSE 3001
CMD ["node", "src/server.js"]
