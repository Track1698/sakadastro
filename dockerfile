# Use the official Python image as the base image
FROM python:3.12.0

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app

# Expose port 8080 for the Flask app
EXPOSE 8080


# Command to run the application
CMD ["python", "app.py"]
