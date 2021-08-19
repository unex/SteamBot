FROM python:3.8

COPY . /app
WORKDIR /app

RUN pip install pipenv
RUN pipenv install --system --deploy

CMD ["python", "bot.py"]
