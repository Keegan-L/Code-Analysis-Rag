import datetime

def log_data(data_type, data):
    timestamp = datetime.datetime.now().isoformat()
    with open(f"{data_type}_log.txt", "a") as f:
        f.write(f"{timestamp} - {data}\n")

