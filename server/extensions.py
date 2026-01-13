from flask_socketio import SocketIO

# Initialize SocketIO without app, will be attached later in factory
socketio = SocketIO(ping_interval=25, ping_timeout=60)
