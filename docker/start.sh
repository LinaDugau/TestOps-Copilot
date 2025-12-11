#!/bin/bash

# Создаем директории для логов
mkdir -p /var/log/supervisor

# Выводим информацию о запуске
echo "=========================================="
echo "TestOps Copilot запущен"
echo "=========================================="
echo ""
echo "Приложение доступно по адресу:"
echo "   http://localhost"
echo ""
echo "=========================================="
echo ""

# Запускаем supervisor
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf

