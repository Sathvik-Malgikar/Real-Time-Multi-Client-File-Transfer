import socket
import hashlib
import os
import json
import random
import time
import logging
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('FileTransferServer')

class FileTransferServer:
    """Server class for handling file transfers using TCP sockets."""
    
    def __init__(self, host: str = 'localhost', port: int = 9999, chunk_size: int = 1024, 
                 simulate_errors: bool = False, error_rate: float = 0.1):
        """
        Initialize the server with configuration parameters.
        
        Args:
            host: Server hostname or IP address
            port: Server port number
            chunk_size: Size of chunks for file splitting
            simulate_errors: Whether to simulate network errors
            error_rate: Probability of simulating an error for each chunk
        """
        self.host = host
        self.port = port
        self.chunk_size = chunk_size
        self.simulate_errors = simulate_errors
        self.error_rate = error_rate
        self.socket = None
        
    def start(self) -> None:
        """Start the server and listen for connections."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            logger.info(f"Server started on {self.host}:{self.port}")
            
            while True:
                client_socket, address = self.socket.accept()
                logger.info(f"Connection established with {address}")
                self.handle_client(client_socket)
                
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            if self.socket:
                self.socket.close()
                logger.info("Server socket closed")
    
    def calculate_checksum(self, file_path: str) -> str:
        """
        Calculate the SHA-256 checksum of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hexadecimal representation of the file's checksum
        """
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(8192)  # Read in 8KB chunks for efficiency
                if not data:
                    break
                sha256.update(data)
                
        return sha256.hexdigest()
    
    def split_file(self, file_path: str) -> List[Tuple[int, bytes]]:
        """
        Split a file into chunks for transmission.
        
        Args:
            file_path: Path to the file to be split
            
        Returns:
            List of (sequence_number, chunk_data) tuples
        """
        chunks = []
        sequence_number = 0
        
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                chunks.append((sequence_number, chunk))
                sequence_number += 1
                
        return chunks
    
    def send_response(self, client_socket: socket.socket, response: Dict) -> None:
        """
        Send a JSON response to the client.
        
        Args:
            client_socket: Socket connected to the client
            response: Dictionary containing the response data
        """
        response_json = json.dumps(response).encode('utf-8')
        client_socket.sendall(len(response_json).to_bytes(4, byteorder='big'))
        client_socket.sendall(response_json)
    
    def receive_request(self, client_socket: socket.socket) -> Dict:
        """
        Receive a JSON request from the client.
        
        Args:
            client_socket: Socket connected to the client
            
        Returns:
            Dictionary containing the request data
        """
        msg_len_bytes = client_socket.recv(4)
        msg_len = int.from_bytes(msg_len_bytes, byteorder='big')
        
        chunks = []
        bytes_received = 0
        
        while bytes_received < msg_len:
            chunk = client_socket.recv(min(msg_len - bytes_received, 4096))
            if not chunk:
                raise ConnectionError("Connection closed while receiving data")
            chunks.append(chunk)
            bytes_received += len(chunk)
            
        request_data = b''.join(chunks).decode('utf-8')
        return json.loads(request_data)
    
    def handle_client(self, client_socket: socket.socket) -> None:
        """
        Handle client connection and file transfer requests.
        
        Args:
            client_socket: Socket connected to the client
        """
        try:
            while True:
                # Receive the request from the client
                request = self.receive_request(client_socket)
                command = request.get('command')
                
                if command == 'upload':
                    self.handle_upload(client_socket, request)
                elif command == 'disconnect':
                    logger.info("Client requested disconnection")
                    break
                else:
                    logger.warning(f"Unknown command: {command}")
                    self.send_response(client_socket, {
                        'status': 'error',
                        'message': f"Unknown command: {command}"
                    })
        except ConnectionError as e:
            logger.info(f"Client disconnected: {e}")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            client_socket.close()
            logger.info("Client connection closed")
    
    def handle_upload(self, client_socket: socket.socket, request: Dict) -> None:
        """
        Handle a file upload request from the client.
        
        Args:
            client_socket: Socket connected to the client
            request: Dictionary containing the request data
        """
        try:
            file_path = request.get('file_path', '')
            file_data = request.get('file_data', '')
            
            if not file_path or not file_data:
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Missing file path or file data'
                })
                return
            
            # Save the uploaded file to a temporary location
            temp_file_path = f"server_{os.path.basename(file_path)}"
            with open(temp_file_path, 'wb') as f:
                f.write(file_data.encode('latin1'))  # Using latin1 to preserve binary data
            
            logger.info(f"File received and saved as {temp_file_path}")
            
            # Calculate the checksum
            checksum = self.calculate_checksum(temp_file_path)
            logger.info(f"Calculated checksum: {checksum}")
            
            # Split the file into chunks
            chunks = self.split_file(temp_file_path)
            logger.info(f"File split into {len(chunks)} chunks")
            
            # Send the response with metadata
            self.send_response(client_socket, {
                'status': 'ready',
                'checksum': checksum,
                'total_chunks': len(chunks),
                'file_path': file_path
            })
            
            # Send the chunks to the client
            random.shuffle(chunks)  # Simulate out of order packets
            
            for seq_num, chunk_data in chunks:
                # Simulate network errors if enabled
                if self.simulate_errors and random.random() < self.error_rate:
                    if random.random() < 0.5:
                        # Skip sending this chunk (packet loss)
                        logger.info(f"Simulating packet loss for chunk {seq_num}")
                        continue
                    else:
                        # Corrupt the chunk data (bit flips)
                        logger.info(f"Simulating data corruption for chunk {seq_num}")
                        corrupted_data = bytearray(chunk_data)
                        # Flip some random bits
                        for _ in range(min(10, len(corrupted_data))):
                            pos = random.randint(0, len(corrupted_data) - 1)
                            corrupted_data[pos] ^= random.randint(1, 255)
                        chunk_data = bytes(corrupted_data)
                
                # Small delay to simulate network latency
                time.sleep(0.01)
                
                # Send each chunk with its sequence number
                chunk_msg = {
                    'type': 'chunk',
                    'sequence': seq_num,
                    'data': chunk_data.hex()  # Convert binary data to hex string
                }
                self.send_response(client_socket, chunk_msg)
                
            # Send an 'end of transmission' message
            self.send_response(client_socket, {
                'type': 'end',
                'message': 'File transmission complete'
            })
            
            # Clean up the temporary file
            os.remove(temp_file_path)
            logger.info(f"Temporary file {temp_file_path} removed")
            
        except Exception as e:
            logger.error(f"Error in file upload: {e}")
            self.send_response(client_socket, {
                'status': 'error',
                'message': f"Server error: {str(e)}"
            })

if __name__ == "__main__":
    # Create and start the server
    server = FileTransferServer(
        host='localhost',
        port=9999,
        chunk_size=1024,
        simulate_errors=True,  # Set to True to simulate network errors
        error_rate=0.1  # 10% chance of error for each chunk
    )
    server.start()