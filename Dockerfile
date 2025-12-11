# Multi-stage build для объединения frontend и backend

# Stage 1: Сборка frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Копируем package files
COPY frontend/package*.json ./

# Устанавливаем зависимости
RUN npm install

# Копируем исходники frontend
COPY frontend/ ./

# Собираем production build
RUN npm run build

# Stage 2: Backend и финальный образ
FROM python:3.12-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем и устанавливаем Python зависимости
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем backend код
COPY backend/ ./backend/

# Копируем собранный frontend из предыдущего stage
COPY --from=frontend-builder /app/frontend/build /usr/share/nginx/html

# Копируем конфигурацию nginx
COPY frontend/nginx.conf /etc/nginx/sites-available/default
RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Копируем конфигурацию supervisor для управления процессами
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Создаем скрипт запуска
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

# Открываем порты
EXPOSE 80

# Запускаем supervisor, который управляет nginx и uvicorn
CMD ["/start.sh"]

