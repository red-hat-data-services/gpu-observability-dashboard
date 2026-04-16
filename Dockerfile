FROM registry.access.redhat.com/ubi9/python-312:latest

WORKDIR /opt/app-root/src

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py chat_ui.py gpu_tools.py mcp_server.py user_view.py data_live.py demo_runner.py ./

# Streamlit config — ensure .streamlit dir is writable for arbitrary UIDs (OpenShift)
RUN mkdir -p $HOME/.streamlit && \
    printf '[server]\nheadless = true\nport = 8501\naddress = "0.0.0.0"\nenableCORS = false\nenableXsrfProtection = false\n\n[browser]\ngatherUsageStats = false\n' > $HOME/.streamlit/config.toml && \
    chmod -R g+w $HOME/.streamlit

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
