FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt file (adjust this if you use a different name)
COPY requirements.txt requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your app files into the container
COPY . .

# Command to start your Flask app
CMD ["flask", "run", "--host=0.0.0.0"]

# Expose the port your app runs on (default Flask port is 5000)
EXPOSE 5000
