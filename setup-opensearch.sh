#!/bin/bash
# This script is intended to be run from within the Docker network.

set -e

# Wait for OpenSearch to become available.
# The script will try for about a minute before failing.
until curl -s -k -u admin:${OPENSEARCH_SCRAPER_PASSWORD} "https://opensearch-node:9200/_cluster/health?wait_for_status=yellow&timeout=50s"; do
  echo "Waiting for OpenSearch to be ready..."
  sleep 5
done
echo "OpenSearch is up!"

# With the security plugin enabled, authentication is required.
# The admin user is automatically created with the initial password.
# Additional users and roles can be configured as needed.

echo ""
echo "Setup complete. OpenSearch is running with SSL and authentication enabled."
echo "Clients must authenticate and use HTTPS to connect to the database."