FROM registry.access.redhat.com/ubi9/python-312:latest

WORKDIR /opt/app-root/src

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py chat_ui.py gpu_tools.py mcp_server.py user_view.py data_live.py ./

# Streamlit config (UBI runs as non-root user 1001)
RUN mkdir -p $HOME/.streamlit && \
    printf '[server]\nheadless = true\nport = 8501\naddress = "0.0.0.0"\nenableCORS = false\nenableXsrfProtection = false\n' > $HOME/.streamlit/config.toml

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
