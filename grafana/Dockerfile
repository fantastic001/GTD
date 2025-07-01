FROM python:3.9-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates unzip gnupg && \
    curl -fsSL https://rclone.org/install.sh | bash && \
    rclone --version && \
    apt-get purge -y gnupg && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash appuser
USER appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["/usr/local/bin/python", "-m", "gtd", "serve_http"]