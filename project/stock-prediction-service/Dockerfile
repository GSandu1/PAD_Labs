# Use Node.js 18 as the base image
FROM node:18

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json to install dependencies
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application files (including .proto and index.js)
COPY . .

# Expose port 5000 for the service
EXPOSE 5000

# Command to run your service
CMD ["node", "index.js"]
