FROM node:20-alpine AS build

WORKDIR /app
COPY package.json ./

ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

ARG VITE_KEYCLOAK_ISSUER_URL
ENV VITE_KEYCLOAK_ISSUER_URL=${VITE_KEYCLOAK_ISSUER_URL}

ARG VITE_KEYCLOAK_CLIENT_ID
ENV VITE_KEYCLOAK_CLIENT_ID=${VITE_KEYCLOAK_CLIENT_ID}

RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
