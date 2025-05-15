FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install flask python-dotenv requests

CMD ["flask", "run", "--host=0.0.0.0"]
