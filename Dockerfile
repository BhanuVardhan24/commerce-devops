FROM python:3.14.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv
COPY requirements.txt ./

RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip uninstall -y pip \
    && groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid appuser --no-create-home appuser

COPY --chown=10001:10001 app/ ./app/
USER 10001:10001
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "app.main:create_app()"]
