# DataQnA 前端镜像：pnpm 构建 → nginx 静态托管 + /api 反向代理
FROM node:22-alpine AS build

RUN corepack enable
WORKDIR /app

# 先装依赖（利用层缓存）
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# 拷贝源码并构建
COPY . .
RUN pnpm build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
