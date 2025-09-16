# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install pip requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "stream_app.py", "--server.port=8501", "--server.address=0.0.0.0"]