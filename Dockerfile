FROM postgres:15

# Install any additional tools if needed
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Expose PostgreSQL port
EXPOSE 5432 