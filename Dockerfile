FROM python:3.11

ENV PYTHONUNBUFFERED=1

RUN pip install poetry==1.5.1
RUN poetry config virtualenvs.create false

RUN mkdir /code
COPY pyproject.toml poetry.lock /code/
WORKDIR /code

RUN poetry install --no-interaction --no-root

COPY ./ /code/

CMD python -m spamgpt.cli
