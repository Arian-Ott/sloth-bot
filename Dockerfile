# Start from a base image
FROM python:3.12-slim

# Install git
RUN apt-get update && apt-get install -y git && apt-get clean

# Copy the requirements first to save time on rebuilds
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Prevents the reinstallation of dependencies unless requirements.txt changes
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
# Now copy the rest of the files
COPY . .

# Command to run your application
CMD ["python", "main.py"]