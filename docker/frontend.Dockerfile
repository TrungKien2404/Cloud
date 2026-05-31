# Stage 1: Build the React application
FROM node:20-alpine AS build

WORKDIR /app

# Copy package JSON files and install dependencies
COPY frontend-react/package*.json ./
RUN npm install

# Copy the rest of the application files and build
COPY frontend-react/ ./
RUN npm run build

# Stage 2: Serve the static files using Nginx
FROM nginx:alpine

# Copy the build output to Nginx's default public directory
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
