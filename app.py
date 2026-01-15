import eventlet
eventlet.monkey_patch()

import socket
from server import create_app, socketio

app = create_app()

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5000
    
    # Get IP address for display
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    
    print("\n" + "="*50)
    print(f"🚀 GAME SERVER STARTED!")
    print(f"📱 Local:   http://localhost:{port}")
    print(f"🔗 Network: http://{IP}:{port}")
    print("="*50 + "\n")
    
    socketio.run(app, host=host, port=port, debug=True, use_reloader=False)