launch instructions:
server:


uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload



client:

python -m client.main  or  flet run client
