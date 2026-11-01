# Восстановленные функциональные требования (REQUIREMENTS.md)

Требования сформулированы на основе анализа исходного кода. Каждое требование описывает конкретное поведение системы с привязкой к коду.

## Основные сценарии взаимодействия пользователя с приложением
- **Сценарий 1. Просмотр списка акций (анонимный/авторизованный)**: пользователь открывает главную страницу `/` - система отображает список акций, отсортированный по `name`, с пагинацией по 100 элементов.
- **Сценарий 2. Просмотр детальной страницы акции**: пользователь переходит по ссылке на акцию - система отображает страницу с графиком, построенным через `get_graph(share)`.
- **Сценарий 3. Добавление акции (только авторизованный)**: авторизованный пользователь переходит на `/create` - заполняет форму `ShareModelForm` и создаёт акцию. Неавторизованный перенаправляется на главную.
- **Сценарий 4. Редактирование/удаление акции (только авторизованный)**: авторизованный пользователь редактирует/удаляет акцию через соответствующие страницы.
- **Сценарий 5. Работа с REST API**: клиент запрашивает `/api/v1/shares/` с возможностью фильтрации по `name`/`ticker`, поиска, сортировки.
- **Сценарий 6. Загрузка акций из Tinkoff API**: администратор запускает `python manage.py add_shares` для первоначальной загрузки инструментов.
- **Сценарий 7. Автоматическое обновление цен**: Celery beat периодически вызывает `update_last_price()` для обновления `last_price` и `is_trend_high` всех акций.

## Бизнес-правила, проверки и ограничения
- **BR-01**: CRUD-операции по акциям (создание/редактирование/удаление) доступны только аутентифицированным пользователям. Неаутентифицированные перенаправляются на `dashboard:index`.
- **BR-02**: `ShareListView` использует пагинацию `paginate_by=100` и сортировку `ordering=["name"]`.
- **BR-03**: Уникальность `figi`, `ticker`, `uid` у акции (определено в модели).
- **BR-04**: При обновлении цен определяется тренд: если новый `last_price` >= предыдущего - `is_trend_high=True`, иначе `False`. При ошибке сравнения/получения данных применяется обработка с логированием.
- **BR-05**: REST API использует глобальную пагинацию `LimitOffsetPagination` с `PAGE_SIZE=100`.
- **BR-06**: Доступ к админке предоставляется через `/admin/`.
- **BR-07**: Для работы с Tinkoff API требуется `TINKOFF_TOKEN` (в текущей конфигурации берётся из настроек/env).

## Функциональные требования

### FR-01. Просмотр списка акций
- **Описание**: Система должна отображать список акций, отсортированный по полю `name`. Для списка используется пагинация по 100 элементов на страницу.
- **Реализация**: `dashboard/views.py:20-28` - `ShareListView` (model=Share, template_name="dashboard/list.html", paginate_by=100, ordering=["name"])
- **URL**: `dashboard/urls.py:14` - `path("", ShareListView.as_view(), name="index")` (подключен в `config/urls.py:6` как корневой)

### FR-02. Просмотр детальной информации об акции с графиком
- **Описание**: При запросе детальной страницы акции по `pk` система должна отобразить страницу с графиком для данной акции, используя `get_graph(share)`.
- **Реализация**: `dashboard/views.py:29-39` - `ShareDetailView.get()` загружает `Share.objects.get(id=pk)`, рендерит `dashboard/detail.html` с контекстом `{"plot_div": get_graph(share), "share": share}`
- **Сервис**: `dashboard/services/graph.py` (содержит функцию `get_graph`) - используется для построения графика
- **URL**: `dashboard/urls.py:15` - `path("<int:pk>", ShareDetailView.as_view(), name="detail")`

### FR-03. Создание акции (только для аутентифицированных)
- **Описание**: Добавление новой акции доступно только аутентифицированным пользователям. Неаутентифицированный пользователь при попытке доступа должен быть перенаправлен на `dashboard:index`.
- **Реализация**: `dashboard/views.py:11-18` - `IsUserAuthenticatedMixin` (проверка `self.request.user.is_authenticated`, `handle_no_permission()` возвращает `redirect("dashboard:index")`). `dashboard/views.py:41-47` - `ShareCreateView(IsUserAuthenticatedMixin, CreateView)` с `form_class = ShareModelForm`, `template_name="dashboard/create.html"`, `success_url = reverse_lazy("dashboard:index")`
- **URL**: `dashboard/urls.py:16` - `path("create", ShareCreateView.as_view(), name="create")`

### FR-04. Редактирование акции (только для аутентифицированных)
- **Описание**: Редактирование акции доступно только аутентифицированным пользователям с редиректом неаутентифицированных на `dashboard:index`. Используется та же форма `ShareModelForm` и тот же шаблон создания.
- **Реализация**: `dashboard/views.py:49-56` - `ShareUpdateView(IsUserAuthenticatedMixin, UpdateView)`, `model=Share`, `template_name="dashboard/create.html"`, `form_class=ShareModelForm`, `success_url=reverse_lazy("dashboard:index")`
- **URL**: `dashboard/urls.py:17` - `path("update/<int:pk>", ShareUpdateView.as_view(), name="update")`

### FR-05. Удаление акции (только для аутентифицированных)
- **Описание**: Удаление акции доступно только аутентифицированным пользователям с редиректом неаутентифицированных на `dashboard:index`.
- **Реализация**: `dashboard/views.py:58-63` - `ShareDeleteView(IsUserAuthenticatedMixin, DeleteView)`, `model=Share`, `template_name="dashboard/delete.html"`, `success_url=reverse_lazy("dashboard:index")`
- **URL**: `dashboard/urls.py:18` - `path("delete/<int:pk>", ShareDeleteView.as_view(), name="delete")`

### FR-06. REST API для акций
- **Описание**: Система предоставляет REST API для работы с акциями через DRF ViewSet с поддержкой фильтрации, поиска, сортировки и пагинации.
- **Реализация**: `dashboard/api/v1/views.py:16-22` - `ShareViewSet` (serializer_class=ShareSerializer, queryset=Share.objects.all(), filter_backends включают OrderingFilter, DjangoFilterBackend, SearchFilter, filterset_class=ShareFilter, ordering_fields=["name","ticker"], search_fields=["$name"]). `dashboard/api/v1/serializer.py:6-19` - `ShareSerializer` со всеми полями модели. Пагинация настроена глобально в `config/settings.py:31-35` (LimitOffsetPagination, PAGE_SIZE=100). Фильтр по `name`, `ticker` в `ShareFilter` (`dashboard/api/v1/views.py:10-13`).
- **URL**: `dashboard/urls.py:19` - `path("api/", include("dashboard.api.urls"))`; `dashboard/api/v1/router.py` и `dashboard/api/v1/urls.py` настраивают роутинг ViewSet (доступен по маршрутам API v1).

### FR-07. Загрузка списка акций из Tinkoff Invest API
- **Описание**: Система должна уметь загружать инструменты-акции из Tinkoff Invest API и сохранять их в БД через management-команду, избегая дубликатов.
- **Реализация**: `dashboard/management/commands/add_shares.py:8-24` - команда `add_shares` использует `Client(TINKOFF_TOKEN)`, получает `client.instruments.shares()`, для каждой записи выполняет `Share.objects.get_or_create(figi=share.figi, name=share.name, isin=share.isin, ticker=share.ticker, currency=share.currency, uid=share.uid)`. Токен берется из `config/settings.py:134` (`TINKOFF_TOKEN = ""`).
- **Использование**: `README.md:10` - `python manage.py add_shares`

### FR-08. Периодическое обновление цен акций через Celery
- **Описание**: Система должна периодически обновлять текущие цены акций через фоновую задачу Celery. Для каждой акции определяется тренд (повышение/понижение цены) по сравнению с предыдущим значением `last_price`.
- **Реализация**: `config/celery.py:13-18` - beat_schedule с задачей `dashboard.tasks.update_last_price` каждые 10.0 секунд. `dashboard/tasks.py:7-28` - задача получает все акции, для каждой вызывает `get_last_data(share)`, сравнивает с `share.last_price` (если текущее `share.last_price > last_price` то `is_trend_high = False`, иначе `True`; при ошибке сравнения `is_trend_high = True` и логируется ошибка), обновляет через `Share.objects.filter(id=share.id).update(last_price=last_price, is_trend_high=is_trend_high)`. Логирование через `config.settings.logger`.
- **Получение данных**: `dashboard/services/market_data.py:6-11` - `get_last_data()` использует `Client(TINKOFF_TOKEN)`, вызывает `client.market_data.get_last_prices(figi=[share.figi])`, возвращает `[resp.price.units, resp.time]`.

### FR-09. Администрирование через Django Admin
- **Описание**: Система использует стандартный Django Admin (`config/urls.py:5` - `path("admin/", admin.site.urls)`). Приложения подключены в `INSTALLED_APPS` (`config/settings.py:13-26`).
- **Реализация**: `config/urls.py:1,5`, `config/settings.py:14,22,23`.

### FR-10. Аутентификация/приложение пользователя
- **Описание**: Проект содержит приложение `user` (подключено в `INSTALLED_APPS`, URL в корне как `path("user", include("user.urls"))` в `config/urls.py:7`). 
- **Реализация**: `config/settings.py:23`, `config/urls.py:7`, структура `user/` (views/forms/urls/models/apps).
- **Примечание**: детальная функциональность приложения `user` не полностью раскрыта в прочитанном коде (модели не детализированы) - см. раздел "Выявленные неоднозначности и дефекты реализации".

## Выявленные неоднозначности и дефекты реализации

### Неоднозначности
- **Дефект/особенность в URL для user**: в `config/urls.py:7` использован `path("user", include("user.urls"))` без завершающего слеша. Это может приводить к неожиданным маршрутам в зависимости от настроек, но это именно особенность текущей реализации - **не является требованием**, отмечается как неоднозначность/особенность.
- **Модели в user**: файл `user/models.py` существует, но явные кастомные модели не прочитаны. **Предположение**: используются встроенные модели `auth.User` (стандартная практика). Требуется перепроверить при модификации, но на основе текущего кода нельзя однозначно утверждать наличие кастомных моделей.
- **Обработка отсутствия прав в миксине**: `IsUserAuthenticatedMixin.handle_no_permission()` возвращает `redirect("dashboard:index")` как статический метод (но в Django принято переопределять `handle_no_permission` как метод экземпляра или использовать `login_url`). Это работает в текущей реализации, но является не совсем типичным подходом - **особенность реализации**.
- **Токен Tinkoff**: `TINKOFF_TOKEN = ""` в `config/settings.py:134`. Для работы команд/задач, использующих API, требуется реальный токен. В коде нет проверок/валидации - **предположение о необходимости настройки**.
- **БД по умолчанию**: настроен PostgreSQL, закомментирован SQLite. Для запуска без внешних сервисов может потребоваться переключение или наличие Postgres - **особенность окружения**.
- **Celery beat интервал**: в `config/celery.py:16` указан `schedule: 10.0` секунд (очень частый для продакшна), в комментарии README упоминается "каждые 5 мин" в описании, но фактический интервал в коде - 10 секунд - **расхождение между документацией и реализацией** (неоднозначность).

### Дефекты реализации
- **Опечатка в переменной**: в `dashboard/tasks.py:13` используется `[last_price, detetime] = get_last_data(share)`. Переменная названа `detetime` вместо `datetime` - опечатка. Фактически значение времени не используется, но это дефект наименования.
- **Опасное сравнение цен**: в `dashboard/tasks.py:16-22` сравнение `if share.last_price > last_price:` происходит до проверки на `None`. Если `share.last_price` или `last_price` равны `None`, сравнение может вызвать проблемы; при исключении логируется ошибка и `is_trend_high` устанавливается в `True` по умолчанию - некорректная/неочевидная логика обработки отсутствующих цен.
- **Отсутствие обработки None в get_last_data**: `dashboard/services/market_data.py:9-11` делает `resp.last_prices.pop()` и возвращает `[resp.price.units, resp.time]` без проверок. При пустом ответе API будет ошибка.
- **Потенциальная ошибка в DetailView**: `dashboard/views.py:32` использует `Share.objects.get(id=pk)` без обработки `DoesNotExist` - при несуществующей акции будет 404 через стандартное поведение Django, но явной обработки нет (может быть дефектом в общем случае).
- **Поиск в API**: `dashboard/api/v1/views.py:22` использует `search_fields = ["$name"]` с префиксом `$` для регистронезависимого поиска по имени в DRF - корректно для DRF, но требует проверки совместимости; при неправильной конфигурации может не работать. Отмечается как потенциальный момент.
- **manage.py сообщение об ошибке**: `manage.py:14` упоминает "DjangoOld" в тексте исключения - опечатка/устаревший текст сообщения (косметический дефект).
- **Логирование в файл**: `config/settings.py:49-52` использует `FileHandler` с `filename="app.logs"` (относительный путь) - может создавать файл в рабочей директории, при отсутствии прав/в разных окружениях потенциальная проблема.
- **settings.py секреты**: `SECRET_KEY = ""` и `TINKOFF_TOKEN = ""` пустые - критично для запуска в продакшне, но для локальной разработки/тестов это дефект конфигурации.
- **ALLOWED_HOSTS пуст**: `config/settings.py:10` `ALLOWED_HOSTS = []` при `DEBUG=True` в Django 4.x работает, но в общем случае требует внимания.
- **Нет явных миграций в обзорe**: миграции есть в `dashboard/migrations/` (папка существует), но содержимое не читалось полностью - требование проверить актуальность миграций при модернизации (задача 3.3).
- **requirements.txt содержит старые версии**: Django 4.1.7, DRF 3.14.0, Celery 5.2.7, psycopg2-binary 2.9.5, redis 4.5.1 и др. - требуют обновления под Python 3.11+ согласно задаче 3.2.
