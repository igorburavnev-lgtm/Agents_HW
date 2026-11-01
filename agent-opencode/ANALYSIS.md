# Анализ исходного кода (Investing Demo)

## 1. Назначение приложения и используемый технологический стек

### Назначение
Проект "investing" предназначен для работы с акциями и получения котировок через Tinkoff Invest API. Включает веб-интерфейс для просмотра/добавления/редактирования/удаления акций (`dashboard`), авторизацию/профиль пользователя (`user`), REST API для акций, периодическое обновление цен через Celery, а также построение графиков.

### Технологический стек
- **Python** - язык разработки
- **Django** - веб-фреймворк (после модернизации обновлён)
- **Django REST framework** - REST API
- **django-filter** - фильтрация
- **Celery + Redis** - фоновые задачи и планировщик
- **PostgreSQL/SQLite** - БД
- **Tinkoff Invest API** (`tinkoff-investments`) - интеграция с API Тинькофф
- **django-crispy-forms, crispy-bootstrap3, plotly** - UI и графики

## 2. Структура проекта, основные компоненты и их назначение

### Корень
- `manage.py` - точка входа Django
- `config/` - конфигурация проекта
- `dashboard/` - основное приложение (акции, API, задачи, сервисы)
- `user/` - приложение пользователя
- `requirements.txt` - зависимости
- `docker-compose.yml` - инфраструктура

### config/
- `settings.py` - настройки
- `urls.py` - корневые маршруты
- `celery.py` - конфигурация Celery и beat-расписание
- `wsgi.py/asgi.py` - WSGI/ASGI

### dashboard/
- `models.py` - модели (Share, Portfolio, Position, Transaction)
- `views.py` - CBV для веб-интерфейса
- `urls.py` - маршруты веб и API
- `forms.py` - формы
- `admin.py` - админка
- `tasks.py` - Celery-задачи
- `api/v1/` - DRF ViewSet'ы, сериализаторы, роутеры
- `management/commands/add_shares.py` - загрузка акций из Tinkoff API
- `services/market_data.py`, `services/graph.py` - бизнес-логика
- `migrations/` - миграции
- `templates/`, `static/` - шаблоны и статика

### user/
- Приложение для работы с пользователем (подключено через URL и INSTALLED_APPS)

**Связь**: `config.urls` включает `dashboard.urls` и `user.urls`; `dashboard` использует `config.settings` и `config.celery`; `user` интегрирован в проект.

## 3. Архитектура приложения и взаимодействие компонентов
1. HTTP-запрос -> `config.urls` -> `dashboard.urls` (веб CBV) или `dashboard.api.urls` (DRF)
2. View/ViewSet -> ORM через модели Django
3. Для детальной страницы вызывается `services.graph.get_graph()`
4. Celery: `config.celery` определяет beat-расписание для `dashboard.tasks.update_last_price()` (обновление цен каждые 10 сек)
5. Tinkoff API: через `tinkoff.invest.Client` в `management/commands/add_shares.py` и `services.market_data.py`

## 4. Используемые библиотеки и внешние зависимости
См. `requirements.txt` и `MODERNIZATION.md` (таблица актуализации).

## 5. Модель данных: сущности, атрибуты и связи
### Share (dashboard/models.py)
- figi (Char, unique), isin (Char), name (Char), ticker (Char, unique), currency (Char), uid (Char, unique)
- last_price (Float, null), is_trend_high (Boolean, null), updated_at (DateTime, auto_now)
- Связей нет

### Portfolio (добавлен)
- user (FK to AUTH_USER_MODEL, CASCADE), name (Char), created_at, updated_at
- Связь 1:N с Position, Transaction

### Position (добавлен)
- portfolio (FK to Portfolio, CASCADE), share (FK to Share, PROTECT), quantity (Decimal), avg_buy_price (Decimal), timestamps
- unique_together (portfolio, share)

### Transaction (добавлен)
- portfolio (FK), share (FK), transaction_type (BUY/SELL), quantity, price, total (Decimal), created_at

**Предположение**: `user` использует стандартный `auth.User` без дополнительных кастомных моделей.

## 6. Механизмы обработки пользовательских запросов и взаимодействия с БД
- **ORM**: Django ORM для всех операций с БД
- **Транзакции**: в новой функциональности используется `transaction.atomic()` с `select_for_update()` для консистентности при покупке/продаже
- **Фоновые задачи**: Celery для периодического обновления цен
- **API**: DRF с пагинацией, фильтрацией, поиском, сортировкой

## Восстановленные функциональные требования (краткая сводка)
См. подробный список в `REQUIREMENTS.md` (FR-01..FR-10). Ключевые:
- Просмотр списка/детали акций, CRUD с ограничением для аутентифицированных
- REST API для акций
- Загрузка акций из Tinkoff API
- Периодическое обновление цен через Celery
- Админка и приложение пользователя

## Что изменено при модернизации
- Обновлены зависимости, приведены настройки к совместимости с запуском
- Исправлены `manage.py`, `dashboard/tasks.py`, `dashboard/services/market_data.py`
- Добавлены заглушки `tinkoff.invest` для совместимости
- `python manage.py check` и `python manage.py migrate` проходят успешно

## Что добавлено в новой функциональности
- Модели `Portfolio`, `Position`, `Transaction` (миграция `0008`)
- DRF API для виртуального портфеля (покупка/продажа, позиции/транзакции, сводка с расчётом стоимости и P&L)
- Тесты `dashboard/tests_portfolio.py` (5 тестов)
- Документация `FEATURE_REQUIREMENTS.md`, `FEATURE_REPORT.md`
