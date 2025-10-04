#!/bin/bash
# Regression Test Runner for Sports League Management System

echo "========================================="
echo "Running SLMS Regression Test Suite"
echo "========================================="
echo ""

# Run inside Docker container
docker-compose exec web pytest tests/test_regression_suite.py -v --tb=short --color=yes

echo ""
echo "========================================="
echo "Test run complete!"
echo "========================================="
