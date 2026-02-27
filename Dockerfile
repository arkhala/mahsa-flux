FROM alpine:3.21

RUN apk add --no-cache python3 py3-pip curl unzip && \
    pip3 install --no-cache-dir --break-system-packages flask && \
    curl -L -o /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip && \
    unzip /tmp/xray.zip -d /usr/local/bin && chmod +x /usr/local/bin/xray && rm /tmp/xray.zip

COPY entrypoint.py /entrypoint.py
COPY sub_server.py /sub_server.py
COPY xray_template.json /xray_template.json

EXPOSE 443 8080

CMD ["python3", "/entrypoint.py"]