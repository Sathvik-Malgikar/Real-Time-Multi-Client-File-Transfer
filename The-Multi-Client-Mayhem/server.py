import socket
import threading
import hashlib
import random
import json
import os
import time
from typing import Dict, List, Tuple, Any

# Configuration
HOST = '127.0.0.1'
PORT = 65432
CHUNK_SIZE = 1024
ERROR_RATE = 0.2  # 20% chance of simulated packet error

# Dictionary to store client data
client_data: Dict[str, Dict[str, Any]] = {}

def calculate_checksum(data: bytes) -> str:
    """Calculate SHA256 checksum for data"""
    return hashlib.sha256(data).hexdigest()

def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    """Handle individual client connection"""
    print(f"[NEW CONNECTION] {addr} connected.")
    
    # Generate a unique client ID
    client_id = f"{addr[0]}:{addr[1]}_{int(time.time())}"
    
    try:
        # Receive file data from client
        file_size_data = conn.recv(1024)
        if not file_size_data:
            return
        
        file_size = int(file_size_data.decode())
        print(f"[{addr}] Receiving file of size {file_size} bytes")
        
        # Acknowledge file size
        conn.sendall(b"OK")
        
        # Receive file data
        file_data = b""
        bytes_received = 0
        
        while bytes_received < file_size:
            chunk = conn.recv(min(CHUNK_SIZE, file_size - bytes_received))
            if not chunk:
                break
            file_data += chunk
            bytes_received += len(chunk)
            print(f"[{addr}] Received {bytes_received}/{file_size} bytes")
        
        # Calculate checksum
        checksum = calculate_checksum(file_data)
        print(f"[{addr}] File received. Checksum: {checksum}")
        
        # Store client data
        client_data[client_id] = {
            "file_data": file_data,
            "checksum": checksum,
            "addr": addr
        }
        
        # Send checksum to client
        conn.sendall(checksum.encode())
        
        # Split file into chunks and send them back
        chunks = []
        for i in range(0, len(file_data), CHUNK_SIZE):
            chunks.append(file_data[i:i+CHUNK_SIZE])
        
        # Send number of chunks
        conn.sendall(str(len(chunks)).encode())
        
        # Wait for acknowledgment
        conn.recv(1024)
        
        # Send chunks with error simulation
        for i, chunk in enumerate(chunks):
            # Prepare chunk data with metadata
            chunk_data = {
                "sequence": i,
                "client_id": client_id,
                "data": chunk.hex(),  # Convert bytes to hex string for JSON
                "chunk_checksum": hashlib.md5(chunk).hexdigest()  # Add checksum for each chunk
            }
            
            # Convert to JSON
            json_data = json.dumps(chunk_data).encode()
            
            # Simulate errors (randomly drop or corrupt packets)
            if random.random() < ERROR_RATE:
                error_type = random.choice(["drop", "corrupt"])
                
                if error_type == "drop":
                    print(f"[{addr}] Simulating dropped packet for chunk {i}")
                    # Skip sending this chunk
                    time.sleep(0.1)  # Small delay to simulate network
                    continue
                    
                elif error_type == "corrupt":
                    print(f"[{addr}] Simulating corrupted packet for chunk {i}")
                    # Send corrupted data (modify the checksum)
                    chunk_data["chunk_checksum"] = "corrupted_checksum"
                    json_data = json.dumps(chunk_data).encode()
            
            # Send chunk length first
            conn.sendall(str(len(json_data)).encode())
            
            # Wait for acknowledgment
            conn.recv(1024)
            
            # Send chunk data
            conn.sendall(json_data)
            
            # Wait for acknowledgment before sending next chunk
            ack = conn.recv(1024).decode()
            
            # Handle retransmission requests
            while ack.startswith("RETRANSMIT"):
                seq_num = int(ack.split(":")[1])
                print(f"[{addr}] Retransmitting chunk {seq_num}")
                
                # Prepare chunk data for retransmission (no errors this time)
                chunk_to_resend = chunks[seq_num]
                chunk_data = {
                    "sequence": seq_num,
                    "client_id": client_id,
                    "data": chunk_to_resend.hex(),
                    "chunk_checksum": hashlib.md5(chunk_to_resend).hexdigest()
                }
                
                json_data = json.dumps(chunk_data).encode()
                
                # Send chunk length
                conn.sendall(str(len(json_data)).encode())
                
                # Wait for acknowledgment
                conn.recv(1024)
                
                # Send chunk data
                conn.sendall(json_data)
                
                # Wait for acknowledgment
                ack = conn.recv(1024).decode()
        
        # Final confirmation
        conn.sendall(b"TRANSFER_COMPLETE")
        
        # Receive final confirmation from client
        result = conn.recv(1024).decode()
        print(f"[{addr}] Transfer result: {result}")
        
    except Exception as e:
        print(f"[ERROR] {addr}: {e}")
    finally:
        # Clean up client data after some time
        def cleanup():
            time.sleep(60)  # Keep data for 60 seconds
            if client_id in client_data:
                del client_data[client_id]
                print(f"[CLEANUP] Removed data for client {client_id}")
        
        threading.Thread(target=cleanup, daemon=True).start()
        conn.close()
        print(f"[DISCONNECTED] {addr} disconnected.")

def start_server() -> None:
    """Start the server and listen for connections"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
        server.listen()
        print(f"[LISTENING] Server is listening on {HOST}:{PORT}")
        
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
            
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    print("[STARTING] Server is starting...")
    start_server()