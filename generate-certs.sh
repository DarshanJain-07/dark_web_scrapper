#!/bin/bash

# Script to generate SSL certificates for OpenSearch production setup
# This creates a self-signed CA and certificates for secure communication

set -e

CERTS_DIR="./certs"
DAYS_VALID=3650  # 10 years

echo "Creating certificates directory..."
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

echo "Generating Root CA private key..."
openssl genrsa -out root-ca-key.pem 2048

echo "Generating Root CA certificate..."
openssl req -new -x509 -sha256 -key root-ca-key.pem -out root-ca.pem -days $DAYS_VALID -subj "/C=US/ST=CA/L=San Francisco/O=OpenSearch/OU=Security/CN=root-ca"

echo "Generating OpenSearch node private key..."
openssl genrsa -out opensearch-key.pem 2048

echo "Generating OpenSearch node certificate signing request..."
openssl req -new -key opensearch-key.pem -out opensearch.csr -subj "/C=US/ST=CA/L=San Francisco/O=OpenSearch/OU=Security/CN=opensearch-node"

echo "Creating certificate extensions file..."
cat > opensearch.ext << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = opensearch-node
DNS.2 = localhost
IP.1 = 127.0.0.1
EOF

echo "Generating OpenSearch node certificate..."
openssl x509 -req -in opensearch.csr -CA root-ca.pem -CAkey root-ca-key.pem -CAcreateserial -out opensearch.pem -days $DAYS_VALID -sha256 -extfile opensearch.ext

echo "Setting proper permissions..."
chmod 600 *.pem
chmod 600 *-key.pem

echo "Cleaning up temporary files..."
rm opensearch.csr opensearch.ext

echo "SSL certificates generated successfully!"
echo "Files created in $CERTS_DIR:"
ls -la

echo ""
echo "Certificate information:"
echo "========================"
echo "Root CA:"
openssl x509 -in root-ca.pem -text -noout | grep -A 2 "Subject:"
echo ""
echo "OpenSearch Node:"
openssl x509 -in opensearch.pem -text -noout | grep -A 2 "Subject:"
echo ""
echo "Certificate validity:"
openssl x509 -in opensearch.pem -text -noout | grep -A 2 "Validity"
