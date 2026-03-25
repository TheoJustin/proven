# Use a lightweight Nginx image
FROM nginx:alpine

# Copy the ENTIRE current directory (assets, src, etc.) into the Nginx html folder
COPY . /usr/share/nginx/html

# Expose port 80 inside the container
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]