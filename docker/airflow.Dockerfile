FROM apache/airflow:2.9.3-python3.11

COPY docker/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
