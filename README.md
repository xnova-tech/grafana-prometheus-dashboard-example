# FastAPI + Prometheus + Grafana

Самостоятельный пример XNova показывает полный путь от HTTP-запроса до трёх панелей Grafana. FastAPI-приложение публикует Counter и Histogram на `/metrics`, Prometheus собирает их каждые пять секунд, а provisioned-дашборд отображает RPS, долю HTTP 5xx и p95 задержки.

## Что нужно

- Docker с Compose V2;
- Python 3.12 — только для локальных тестов вне Docker.

Образы и Python-зависимости закреплены точными версиями. Все опубликованные порты привязаны к `127.0.0.1`.

## Запуск

```bash
docker compose config -q
docker compose up --detach --build
docker compose ps
```

Откройте:

- API: <http://127.0.0.1:8000/>;
- метрики: <http://127.0.0.1:8000/metrics>;
- Prometheus targets: <http://127.0.0.1:9090/targets>;
- Grafana: <http://127.0.0.1:3000/>.

Для локального входа в Grafana используйте `admin` / `grafana-demo`. Это публичные демонстрационные учётные данные для loopback-стенда, не конфигурация для production.

Data source `Prometheus` и дашборд `FastAPI monitoring` создаются автоматически. Data source обращается к `http://prometheus:9090` внутри сети Compose.

## Управляемая нагрузка

Запустите четыре профиля по очереди:

```bash
docker compose exec -T app python load.py --mode baseline --seconds 75
docker compose exec -T app python load.py --mode errors --seconds 75
docker compose exec -T app python load.py --mode slow --seconds 75
docker compose exec -T app python load.py --mode recovery --seconds 75
```

Каждый профиль отправляет ровно 450 запросов при стандартной скорости шесть запросов в секунду:

- `baseline` — только HTTP 200;
- `errors` — каждый четвёртый запрос получает намеренный HTTP 503;
- `slow` — каждый третий запрос идёт на маршрут с паузой 350 мс;
- `recovery` — снова только быстрые HTTP 200.

Панели выполняют настоящие PromQL-запросы:

```promql
sum(rate(demo_http_requests_total[1m]))

100 * sum(rate(demo_http_requests_total{status=~"5.."}[1m]))
    / sum(rate(demo_http_requests_total[1m]))

histogram_quantile(
  0.95,
  sum by (le, route) (
    rate(demo_http_request_duration_seconds_bucket[1m])
  )
)
```

## Локальные проверки

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m ruff format --check .
python -m ruff check .
python check_app.py
python -m pytest -q
```

В Windows PowerShell активируйте окружение командой `.venv\Scripts\Activate.ps1`.

`check_app.py` должен завершиться так:

```text
http: 200=ok 404=ok 503=ok slow=ok
metrics: counters=4 histogram=observed scrape_excluded=true
```

## Структура

- `grafana_demo/app.py` — фабрика FastAPI и middleware измерений;
- `grafana_demo/routes.py` — контролируемые HTTP-маршруты и `/metrics`;
- `grafana_demo/metrics.py` — Counter, Histogram и ограниченные labels;
- `grafana_demo/config.py` — проверяемые настройки приложения;
- `grafana_demo/traffic.py` и `load.py` — детерминированные профили нагрузки;
- `grafana/` — provisioning data source и dashboard JSON;
- `tests/` — pytest-контракты через `TestClient` и HTTPX;
- `compose.yaml` и `prometheus.yml` — локальный стенд.

Обычная остановка сохраняет volumes:

```bash
docker compose down
```

Полная очистка состояния:

```bash
docker compose down --volumes
```

Маршрут `/error` намеренно возвращает HTTP 503. Стенд не реализует TLS, production-аутентификацию, алерты или высокую доступность и не предназначен для развёртывания в интернете.

Исходники распространяются по Apache-2.0; условия находятся в `LICENSE`.
