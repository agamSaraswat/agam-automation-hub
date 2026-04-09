@echo off
python -m compileall src tests
cd frontend
npm run typecheck
