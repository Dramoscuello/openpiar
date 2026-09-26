# Etapa 1: compilar la aplicacion Vue
FROM node:22-alpine AS build

WORKDIR /app

# Se usa npm install en lugar de npm ci para resolver dependencias opcionales
# multiplataforma (como bindings nativos/WASM de Tailwind v4 y @emnapi/runtime)
RUN npm install

COPY . .

RUN npm run build


# Etapa 2: servir con Nginx
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
