# 小智 MCP 服务集合 - 统一镜像
FROM python:3.12-slim

WORKDIR /app

# 安装依赖（先复制 requirements，利用构建缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY main.py .
COPY bridge/ bridge/
COPY reminder/ reminder/

# 纯出站 WebSocket，无需开端口
CMD ["python", "main.py"]
