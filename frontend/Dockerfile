# Use official Node.js image as build environment
FROM node:20-alpine AS builder

WORKDIR /app

# Install Yarn
RUN corepack enable

# Copy package.json and yarn.lock (if available)
COPY package.json ./
COPY yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy the rest of the application
COPY . .

# Build the Next.js app
RUN yarn build

# Production image, copy only necessary files
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Install Yarn
RUN corepack enable

# Copy package.json and yarn.lock
COPY package.json ./
COPY yarn.lock ./

# Install only production dependencies
RUN yarn install --frozen-lockfile --production

# Copy built app from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.js ./next.config.js
COPY --from=builder /app/package.json ./package.json
ENV PORT=3002
EXPOSE 3002

CMD ["yarn", "start"]
