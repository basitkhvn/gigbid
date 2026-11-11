FROM node:22-slim AS build
WORKDIR /web
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web ./
ENV STATIC_EXPORT=1 NEXT_PUBLIC_API_URL=
RUN npm run build
FROM nginx:alpine
COPY --from=build /web/out /usr/share/nginx/html
COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf
