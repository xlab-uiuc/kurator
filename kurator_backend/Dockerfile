FROM python:3.10
WORKDIR /kurator_backend

# COPY minimal files needed to setup the app in editable mode
COPY requirements.txt requirements.txt
COPY setup.py setup.py
RUN mkdir kurator
COPY kurator/__init__.py kurator/__init__.py
RUN ls -l
RUN pip install -e .
# COPY . . -- happens in docker-compose.yml
CMD ["python", "kurator/app.py"]
