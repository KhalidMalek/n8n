FROM n8nio/n8n:1.26.0

ENV N8N_BASIC_AUTH_USER=khalid
ENV N8N_BASIC_AUTH_PASSWORD=khalid123
ENV GENERIC_TIMEZONE=Asia/Kolkata
ENV N8N_PORT=8080

EXPOSE 8080

CMD ["n8n", "start", "--port", "8080", "--host", "0.0.0.0"]
