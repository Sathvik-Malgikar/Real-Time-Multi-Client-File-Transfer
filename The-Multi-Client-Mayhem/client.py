import socket
import hashlib
import json
import os
import time
import sys
from typing import Dict, Any, List, Optional

# Configuration
HOST = '127.0.0.1'
PORT = 65432
CHUNK_SIZE = 1024

def calculate_checksum(data: bytes) -> str:
    """Calculate SHA256 checksum for data"""
    return hashlib.sha256(data).hexdigest()

def upload_file(file_path: str) -> None:
    """Upload a file to server and receive it back with integrity check"""
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return
    
    # Create socket
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Connect to server
        client.connect((HOST, PORT))
        print(f"Connected to server at {HOST}:{PORT}")
        
        # Read file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        file_size = len(file_data)
        print(f"File size: {file_size} bytes")
        
        # Send file size
        client.sendall(str(file_size).encode())
        
        # Wait for acknowledgment
        client.recv(1024)
        
        # Send file data
        client.sendall(file_data)
        
        # Receive checksum from server
        server_checksum = client.recv(1024).decode()
        print(f"Server checksum: {server_checksum}")
        
        # Calculate local checksum for verification
        local_checksum = calculate_checksum(file_data)
        print(f"Local checksum: {local_checksum}")
        
        if server_checksum != local_checksum:
            print("Error: Initial checksum mismatch!")
            return
        
        # Receive number of chunks
        num_chunks = int(client.recv(1024).decode())
        print(f"Server will send {num_chunks} chunks")
        
        # Acknowledge
        client.sendall(b"OK")
        
        # Prepare to receive chunks
        chunks: Dict[int, bytes] = {}
        
        for _ in range(num_chunks * 2):  # Allow for retransmissions
            try:
                # Receive chunk length
                chunk_len_data = client.recv(1024)
                if chunk_len_data == b"TRANSFER_COMPLETE":
                    break
                
                chunk_len = int(chunk_len_data.decode())
                
                # Acknowledge chunk length
                client.sendall(b"OK")
                
                # Receive chunk data
                chunk_json_data = client.recv(chunk_len)
                
                # Parse JSON
                try:
                    chunk_info = json.loads(chunk_json_data.decode())
                    sequence = chunk_info["sequence"]
                    client_id = chunk_info["client_id"]
                    data = bytes.fromhex(chunk_info["data"])
                    chunk_checksum = chunk_info["chunk_checksum"]
                    
                    # Verify chunk integrity
                    if hashlib.md5(data).hexdigest() != chunk_checksum:
                        print(f"Chunk {sequence} corrupted, requesting retransmission")
                        client.sendall(f"RETRANSMIT:{sequence}".encode())
                        continue
                    
                    # Store chunk if not already received
                    if sequence not in chunks:
                        chunks[sequence] = data
                        print(f"Received chunk {sequence}/{num_chunks-1}")
                    
                    # Acknowledge successful receipt
                    client.sendall(b"OK")
                    
                    # Check if we have all chunks
                    if len(chunks) == num_chunks:
                        print("All chunks received!")
                        break
                        
                except json.JSONDecodeError:
                    print("Received corrupted JSON, requesting retransmission")
                    client.sendall(b"RETRANSMIT:LAST")
                    continue
                    
            except Exception as e:
                print(f"Error receiving chunk: {e}")
                client.sendall(b"ERROR")
                break
        
        # Final confirmation message
        final_msg = client.recv(1024)
        if final_msg == b"TRANSFER_COMPLETE":
            # Reassemble file
            reassembled_data = b""
            for i in range(num_chunks):
                if i in chunks:
                    reassembled_data += chunks[i]
            
            # Calculate checksum of reassembled file
            reassembled_checksum = calculate_checksum(reassembled_data)
            print(f"Reassembled checksum: {reassembled_checksum}")
            
            # Verify with original checksum
            if reassembled_checksum == server_checksum:
                print("File transfer successful! Checksums match.")
                
                # Save reassembled file with "_received" suffix
                base_name, ext = os.path.splitext(file_path)
                output_path = f"{base_name}_received{ext}"
                
                with open(output_path, 'wb') as f:
                    f.write(reassembled_data)
                
                print(f"File saved as: {output_path}")
                client.sendall(b"SUCCESS")
            else:
                print("Error: Final checksum mismatch!")
                client.sendall(b"CHECKSUM_MISMATCH")
        else:
            print(f"Unexpected final message: {final_msg}")
            client.sendall(b"ERROR")
    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()
        print("Connection closed")

def main() -> None:
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python client.py <file_path>")
        return
    
    file_path = sys.argv[1]
    upload_file(file_path)

if __name__ == "__main__":
    main()