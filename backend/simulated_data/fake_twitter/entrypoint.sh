#!/bin/bash
set -e

uvicorn app:app --host 0.0.0.0 --reload
