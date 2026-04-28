FROM nginx:alpine

# 安装基本工具
RUN apk add --no-cache curl

# 复制配置文件
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# 创建服务静态文件目录
RUN mkdir -p /var/www/services

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
