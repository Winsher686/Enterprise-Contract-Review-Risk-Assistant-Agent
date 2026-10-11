FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（pymupdf 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY backend/requirements.txt /app/requirements.txt

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY knowledge_base/ /app/knowledge_base/
COPY storage/ /app/storage/

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
