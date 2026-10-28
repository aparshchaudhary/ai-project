#!/usr/bin/env bash
# Render Native Build Script
set -o errexit

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Building React frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Build complete."
