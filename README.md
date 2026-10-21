# Напоминания о регламентных задачах

Сервис для хранения повторяющихся задач компаний и автоматической отправки напоминаний ответственным лицам.

## Возможности

- **Модели Company и Task** — компании и их регламентные задачи с настраиваемой периодичностью
- **Автоматические напоминания** — ежедневная Celery-задача находит задачи со сроком в ближайшие 3 дня
- **Email-дайджест** — один ответственный получает одно письмо со всеми своими задачами
- **Защита от дублей** — повторный запуск в тот же день не отправляет письмо повторно
- **Django Admin** — управление задачами, действие «Отметить выполненной» сдвигает следующий срок

## Стек

- Python 3.12, Django 4.2
- PostgreSQL 16
- Redis 7 (брокер Celery)
- Celery + Celery Beat

## Быстрый старт

### Docker Compose

```bash
docker-compose up --build
```

Сервисы:
- **web** — Django на http://localhost:8000
- **db** — PostgreSQL
- **redis** — Redis
- **celery** — воркер Celery
- **beat** — планировщик Celery Beat

### Первый запуск — миграции

```bash
docker compose exec web python manage.py makemigrations tasks
docker compose exec web python manage.py migrate
```

### Создание суперпользователя

```bash
docker compose exec web python manage.py createsuperuser
```

Затем откройте http://localhost:8000/admin/ для управления задачами.

### Запуск задачи вручную

```bash
docker-compose exec celery python -c "
from tasks.tasks import send_reminders
result = send_reminders.delay(days_ahead=3)
print(result.get(timeout=10))
"
```

## Тесты

```bash
# Локально (SQLite, PostgreSQL не нужен)
pip install -r requirements.txt
USE_SQLITE=1 pytest -v

# В Docker
docker-compose exec web pytest -v
```

## Email

По умолчанию используется **console email backend** — письма выводятся в логи контейнера `web`, а не отправляются реально. Чтобы увидеть письмо:

```bash
docker compose logs web --tail 30
```

Это соответствует ТЗ. Для отправки реальных писем замените в `settings.py` бэкенд на SMTP.

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `POSTGRES_HOST` | `db` | Хост PostgreSQL |
| `POSTGRES_DB` | `reminders` | Имя базы данных |
| `POSTGRES_USER` | `postgres` | Пользователь БД |
| `POSTGRES_PASSWORD` | `postgres` | Пароль БД |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | URL брокера Celery |
| `DEFAULT_FROM_EMAIL` | `reminders@example.com` | Адрес отправителя |

## Структура проекта

```
task-reminders/
├── reminders/          # Настройки Django и Celery
│   ├── settings.py
│   ├── celery.py
│   ├── urls.py
│   └── wsgi.py
├── tasks/              # Приложение с моделями и задачами
│   ├── models.py       # Company, Task, SentNotification
│   ├── admin.py        # Django Admin с действием «Выполнено»
│   └── tasks.py        # Celery-задача send_reminders
├── tests/              # Тесты pytest-django
│   ├── test_models.py  # Тесты is_due, mark_completed
│   └── test_tasks.py   # Тесты отправки напоминаний
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
