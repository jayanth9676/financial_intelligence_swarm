import socket

def check_port(host, port):
    print(f"Checking {host}:{port}...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        result = s.connect_ex((host, port))
        if result == 0:
            print("Port is OPEN")
        else:
            print(f"Port is CLOSED (code: {result})")
            # 10061 is refused
    except Exception as e:
        print(f"Error: {e}")
    finally:
        s.close()

if __name__ == "__main__":
    check_port("127.0.0.1", 8000)
    check_port("localhost", 8000)
