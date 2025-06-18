#!/bin/bash

# Script to set up OpenSearch security with custom user for production safety
# This avoids using the common 'admin' username which could expose us

set -e

echo "Setting up OpenSearch security with custom user..."

# Wait for OpenSearch to be ready
echo "Waiting for OpenSearch to be ready..."
until curl -s -k -u admin:admin https://opensearch-node:9200/_cluster/health > /dev/null 2>&1; do
  echo "Waiting for OpenSearch to be ready..."
  sleep 5
done
echo "OpenSearch is ready!"

# Create the custom user using OpenSearch Security API
echo "Creating custom user: ${OPENSEARCH_SCRAPER_USER}"

# Create the custom user with the same password
curl -k -X PUT \
  -u admin:admin \
  -H "Content-Type: application/json" \
  https://opensearch-node:9200/_plugins/_security/api/internalusers/${OPENSEARCH_SCRAPER_USER} \
  -d "{
    \"password\": \"${OPENSEARCH_SCRAPER_PASSWORD}\",
    \"backend_roles\": [],
    \"attributes\": {}
  }"

echo ""
echo "Assigning all_access role to custom user..."

# Assign the all_access role to the custom user
curl -k -X PUT \
  -u admin:admin \
  -H "Content-Type: application/json" \
  https://opensearch-node:9200/_plugins/_security/api/rolesmapping/all_access \
  -d "{
    \"backend_roles\": [],
    \"hosts\": [],
    \"users\": [\"${OPENSEARCH_SCRAPER_USER}\"]
  }"

echo ""
echo "Testing custom user authentication..."

# Test the custom user
if curl -s -k -u ${OPENSEARCH_SCRAPER_USER}:${OPENSEARCH_SCRAPER_PASSWORD} https://opensearch-node:9200/_cluster/health > /dev/null 2>&1; then
  echo "✅ Custom user authentication successful!"
  echo "✅ Security setup complete. Using custom user: ${OPENSEARCH_SCRAPER_USER}"
else
  echo "❌ Custom user authentication failed!"
  exit 1
fi
