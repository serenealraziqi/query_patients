FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies + Python 3.12 and pip/venv
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        curl \
        ca-certificates \
        zip \
        less \
        vim \
        bzip2 \
        build-essential \
        python3.12 \
        python3.12-venv \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Make 'python' and 'pip' point to Python 3.12
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 10 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 10

# Optional: create a virtual environment and use it
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Upgrade packaging tools and install Jupyter Notebook
RUN pip install --upgrade pip setuptools wheel && \
    pip install notebook

SHELL ["/bin/bash", "-c"]

# Workspace
RUN mkdir -p /shared_folder
WORKDIR /shared_folder

# Expose Jupyter port
EXPOSE 8888

# Keep container running by default; uncomment the Jupyter CMD to auto-start
CMD ["tail", "-f", "/dev/null"]
# CMD ["bash", "-lc", "jupyter notebook --ip=0.0.0.0 --no-browser --NotebookApp.token='' --NotebookApp.password='' --allow-root --NotebookApp.allow_origin='*' --notebook-dir=/shared_folder"]                                