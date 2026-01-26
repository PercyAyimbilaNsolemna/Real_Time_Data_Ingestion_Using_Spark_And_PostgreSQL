FROM apache/spark:3.5.0

USER root

# Install Python and pip (not always included by default)
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Make python default
RUN ln -s /usr/bin/python3 /usr/bin/python

# Copy and install requirements
COPY requirements.txt /opt/spark/requirements.txt
RUN pip3 install --no-cache-dir -r /opt/spark/requirements.txt

# Create app & log directories
RUN mkdir -p /opt/spark/app /opt/spark/logs

WORKDIR /opt/spark

USER spark
