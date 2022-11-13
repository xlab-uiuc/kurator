FROM python:3.10
WORKDIR /kurator_backend

# COPY minimal files needed to setup the app in editable mode
COPY requirements.txt requirements.txt
COPY setup.py setup.py
RUN mkdir kurator
COPY kurator/__init__.py kurator/__init__.py
RUN ls -l
RUN pip install -e .

# Install kubeconform
RUN wget https://github.com/yannh/kubeconform/releases/download/v0.5.0/kubeconform-linux-amd64.tar.gz
RUN tar -xvzf kubeconform-linux-amd64.tar.gz
RUN mv kubeconform /usr/local/bin

# COPY . . -- happens in docker-compose.yml
CMD ["python", "kurator/app.py"]
