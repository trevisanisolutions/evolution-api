FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Torna o script executável
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]