import socket
import hashlib
import os
import json
import time
import logging
from typing import Dict, Optional, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('FileTransferClient')

class FileTransferClient:
    """Client class for transferring files using TCP sockets."""
    
    def __init__(self, host: str = 'localhost', port: int = 9999, max_retries: int = 3):
        """
        Initialize the client with configuration parameters.
        
        Args:
            host: Server hostname or IP address
            port: Server port number
            max_retries: Maximum number of retries for failed operations
        """
        self.host = host
        self.port = port
        self.max_retries = max_retries
        self.socket = None
        self.received_chunks = {}
        self.retry_count = 0
        
    def connect(self) -> bool:
        """
        Connect to the server.
        
        Returns:
            True if connection was successful, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to server at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
            
    def disconnect(self) -> None:
        """Disconnect from the server."""
        if self.socket:
            try:
                self.send_request({'command': 'disconnect'})
                self.socket.close()
                logger.info("Disconnected from server")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.socket = None
    
    def send_request(self, request: Dict) -> None:
        """
        Send a JSON request to the server.
        
        Args:
            request: Dictionary containing the request data
        """
        request_json = json.dumps(request).encode('utf-8')
        self.socket.sendall(len(request_json).to_bytes(4, byteorder='big'))
        self.socket.sendall(request_json)
    
    def receive_response(self) -> Dict:
        """
        Receive a JSON response from the server.
        
        Returns:
            Dictionary containing the response data
        """
        msg_len_bytes = self.socket.recv(4)
        if not msg_len_bytes:
            raise ConnectionError("Connection closed by server")
            
        msg_len = int.from_bytes(msg_len_bytes, byteorder='big')
        
        chunks = []
        bytes_received = 0
        
        while bytes_received < msg_len:
            chunk = self.socket.recv(min(msg_len - bytes_received, 4096))
            if not chunk:
                raise ConnectionError("Connection closed while receiving data")
            chunks.append(chunk)
            bytes_received += len(chunk)
            
        response_data = b''.join(chunks).decode('utf-8')
        return json.loads(response_data)
    
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
    
    def calculate_checksum_from_chunks(self, chunks: Dict[int, bytes]) -> str:
        """
        Calculate the SHA-256 checksum from a dictionary of chunks.
        
        Args:
            chunks: Dictionary mapping sequence numbers to chunk data
            
        Returns:
            Hexadecimal representation of the assembled file's checksum
        """
        sha256 = hashlib.sha256()
        
        # Get the sorted sequence numbers
        seq_nums = sorted(chunks.keys())
        
        # Update the hash with each chunk in order
        for seq_num in seq_nums:
            sha256.update(chunks[seq_num])
            
        return sha256.hexdigest()
    
    def upload_file(self, file_path: str) -> bool:
        """
        Upload a file to the server and receive it back in chunks.
        
        Args:
            file_path: Path to the file to be uploaded
            
        Returns:
            True if the file was successfully transferred and verified, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
                
            # Read the file content
            with open(file_path, 'rb') as f:
                file_data = f.read()
                
            # Calculate the original checksum for local verification
            original_checksum = self.calculate_checksum(file_path)
            logger.info(f"Original file checksum: {original_checksum}")
                
            # Send the file upload request
            upload_request = {
                'command': 'upload',
                'file_path': file_path,
                'file_data': file_data.decode('latin1')  # Using latin1 to preserve binary data
            }
            self.send_request(upload_request)
            
            # Receive the server's response
            response = self.receive_response()
            
            if response.get('status') != 'ready':
                logger.error(f"Upload failed: {response.get('message', 'Unknown error')}")
                return False
                
            server_checksum = response.get('checksum')
            total_chunks = response.get('total_chunks')
            
            logger.info(f"Server checksum: {server_checksum}")
            logger.info(f"Expected chunks: {total_chunks}")
            
            # Check if the server's checksum matches the original
            if server_checksum != original_checksum:
                logger.warning("Warning: Server checksum does not match original checksum!")
            
            # Reset the received chunks dictionary
            self.received_chunks = {}
            
            # Process chunks until we receive the 'end' message
            while True:
                chunk_response = self.receive_response()
                
                if chunk_response.get('type') == 'end':
                    logger.info("End of transmission received")
                    break
                    
                if chunk_response.get('type') == 'chunk':
                    seq_num = chunk_response.get('sequence')
                    chunk_data = bytes.fromhex(chunk_response.get('data'))
                    self.received_chunks[seq_num] = chunk_data
                    logger.debug(f"Received chunk {seq_num} of size {len(chunk_data)} bytes")
            
            # Verify we received all chunks
            if len(self.received_chunks) != total_chunks:
                logger.error(f"Missing chunks: received {len(self.received_chunks)} out of {total_chunks}")
                missing_chunks = [i for i in range(total_chunks) if i not in self.received_chunks]
                logger.error(f"Missing sequence numbers: {missing_chunks}")
                
                # Implement retry logic if needed
                if self.retry_count < self.max_retries:
                    self.retry_count += 1
                    logger.info(f"Retrying upload (attempt {self.retry_count}/{self.max_retries})...")
                    return self.upload_file(file_path)
                else:
                    logger.error("Maximum retry count reached, giving up")
                    return False
            
            # Save the received file
            output_file_path = f"received_{os.path.basename(file_path)}"
            self.save_file(output_file_path)
            
            # Calculate checksum of the reassembled file
            reassembled_checksum = self.calculate_checksum(output_file_path)
            logger.info(f"Reassembled file checksum: {reassembled_checksum}")
            
            # Verify the checksum
            if reassembled_checksum == server_checksum:
                logger.info("Checksum verification successful!")
                return True
            else:
                logger.error("Checksum verification failed")
                
                # If verification fails, try again
                if self.retry_count < self.max_retries:
                    self.retry_count += 1
                    logger.info(f"Retrying upload (attempt {self.retry_count}/{self.max_retries})...")
                    return self.upload_file(file_path)
                else:
                    logger.error("Maximum retry count reached, giving up")
                    return False
                
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False
    
    def save_file(self, output_path: str) -> None:
        """
        Save the received chunks to a file.
        
        Args:
            output_path: Path where the reassembled file will be saved
        """
        # Sort the chunks by sequence number
        sorted_keys = sorted(self.received_chunks.keys())
        
        with open(output_path, 'wb') as f:
            for seq_num in sorted_keys:
                f.write(self.received_chunks[seq_num])
                
        logger.info(f"File saved to {output_path}")

    def calculate_checksum_from_memory(self) -> str:
        """
        Calculate the SHA-256 checksum from the chunks in memory.
        
        Returns:
            Hexadecimal representation of the assembled file's checksum
        """
        sha256 = hashlib.sha256()
        
        # Get the sorted sequence numbers
        seq_nums = sorted(self.received_chunks.keys())
        
        # Update the hash with each chunk in order
        for seq_num in seq_nums:
            sha256.update(self.received_chunks[seq_num])
            
        return sha256.hexdigest()


if __name__ == "__main__":
    # Create a client instance
    client = FileTransferClient(
        host='localhost',
        port=9999,
        max_retries=3
    )
    
    try:
        # Connect to the server
        if client.connect():
            # Upload a file
            file_path = input("Enter the path to the file you want to transfer: ")
            start_time = time.time()
            
            if client.upload_file(file_path):
                end_time = time.time()
                logger.info(f"Transfer Successful! Time taken: {end_time - start_time:.2f} seconds")
            else:
                logger.error("Transfer Failed")
                
    except KeyboardInterrupt:
        logger.info("Operation canceled by user")
    finally:
        # Disconnect from the server
        client.disconnect()