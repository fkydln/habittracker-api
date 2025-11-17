FROM python:3.9-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# We copy the whole app
COPY . .

# We add this "FLASK_ENV" to auto-reload
ENV FLASK_ENV=development

# Run the app in debug mode
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001", "--debug"]