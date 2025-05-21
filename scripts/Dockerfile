FROM python:3.11-slim

WORKDIR /tests

COPY . .

RUN pip install -r requirements.txt

CMD ["python", "ezid_ui_tests_remote.py"]


