FROM python:3.11-alpine

COPY . /app
WORKDIR /app

RUN pip install virtualenv pipenv
RUN pipenv install --system --deploy

CMD ["python", "bot.py"]
