import os
import argparse
import logging
from server import FileTransferServer
from client import FileTransferClient
import threading
import time
import tempfile
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('FileTransferDemo')

def create_test_file(file_path, size_kb=10):
    """
    Create a test file of specified size with random content.
    
    Args:
        file_path: Path where the test file will be created
        size_kb: Size of the file in kilobytes
    """
    with open(file_path, 'wb') as f:
        # Generate random data
        data = bytearray(random.getrandbits(8) for _ in range(size_kb * 1024))
        f.write(data)
    
    logger.info(f"Created test file: {file_path} ({size_kb} KB)")

def run_server(host='localhost', port=9999, chunk_size=1024, simulate_errors=False, error_rate=0.1):
    """
    Run the file transfer server.
    
    Args:
        host: Server hostname or IP address
        port: Server port number
        chunk_size: Size of chunks for file splitting
        simulate_errors: Whether to simulate network errors
        error_rate: Probability of simulating an error for each chunk
    """
    server = FileTransferServer(
        host=host,
        port=port,
        chunk_size=chunk_size,
        simulate_errors=simulate_errors,
        error_rate=error_rate
    )
    server.start()

def run_client(file_path, host='localhost', port=9999, max_retries=3):
    """
    Run the file transfer client.
    
    Args:
        file_path: Path to the file to upload
        host: Server hostname or IP address
        port: Server port number
        max_retries: Maximum number of retries for failed operations
        
    Returns:
        True if transfer was successful, False otherwise
    """
    client = FileTransferClient(
        host=host,
        port=port,
        max_retries=max_retries
    )
    
    try:
        # Connect to the server
        if client.connect():
            start_time = time.time()
            
            if client.upload_file(file_path):
                end_time = time.time()
                logger.info(f"Transfer Successful! Time taken: {end_time - start_time:.2f} seconds")
                return True
            else:
                logger.error("Transfer Failed")
                return False
        else:
            logger.error("Connection to server failed")
            return False
                
    except Exception as e:
        logger.error(f"Error in client: {e}")
        return False
    finally:
        # Disconnect from the server
        client.disconnect()

def main():
    """Main function to run the file transfer demo."""
    parser = argparse.ArgumentParser(description='File Transfer System Demo')
    parser.add_argument('--mode', choices=['server', 'client', 'demo'], default='demo',
                        help='Run mode: server, client, or demo (default: demo)')
    parser.add_argument('--host', default='localhost', help='Server host (default: localhost)')
    parser.add_argument('--port', type=int, default=9999, help='Server port (default: 9999)')
    parser.add_argument('--file', help='File path for client mode')
    parser.add_argument('--chunk-size', type=int, default=1024, help='Chunk size in bytes (default: 1024)')
    parser.add_argument('--simulate-errors', action='store_true', help='Simulate network errors')
    parser.add_argument('--error-rate', type=float, default=0.1, help='Error rate for simulation (default: 0.1)')
    parser.add_argument('--max-retries', type=int, default=3, help='Max retries for client (default: 3)')
    parser.add_argument('--test-file-size', type=int, default=10, help='Size of test file in KB (default: 10)')
    
    args = parser.parse_args()
    
    if args.mode == 'server':
        # Run server mode
        run_server(
            host=args.host,
            port=args.port,
            chunk_size=args.chunk_size,
            simulate_errors=args.simulate_errors,
            error_rate=args.error_rate
        )
    
    elif args.mode == 'client':
        # Run client mode
        if not args.file:
            logger.error("--file argument is required in client mode")
            return
            
        run_client(
            file_path=args.file,
            host=args.host,
            port=args.port,
            max_retries=args.max_retries
        )
    
    elif args.mode == 'demo':
        # Run a complete demo with both server and client
        logger.info("Starting demo mode...")
        
        # Create a temporary test file
        temp_dir = tempfile.gettempdir()
        test_file_path = os.path.join(temp_dir, "test_file.dat")
        create_test_file(test_file_path, size_kb=args.test_file_size)
        
        # Start the server in a separate thread
        server_thread = threading.Thread(
            target=run_server,
            args=(args.host, args.port, args.chunk_size, args.simulate_errors, args.error_rate),
            daemon=True
        )
        server_thread.start()
        
        # Give the server time to start
        time.sleep(1)
        
        # Run the client
        try:
            success = run_client(
                file_path=test_file_path,
                host=args.host,
                port=args.port,
                max_retries=args.max_retries
            )
            
            if success:
                print("\n=================================")
                print("🎉 FILE TRANSFER SUCCESSFUL! 🎉")
                print("=================================")
                
                # Verify the received file
                original_path = test_file_path
                received_path = f"received_{os.path.basename(test_file_path)}"
                
                if os.path.exists(received_path):
                    original_size = os.path.getsize(original_path)
                    received_size = os.path.getsize(received_path)
                    
                    print(f"\nOriginal file: {original_path}")
                    print(f"Size: {original_size} bytes")
                    print(f"\nReceived file: {received_path}")
                    print(f"Size: {received_size} bytes")
                    
                    if original_size == received_size:
                        print("\nFile sizes match ✅")
                    else:
                        print("\nFile sizes do not match ❌")
            else:
                print("\n=============================")
                print("❌ FILE TRANSFER FAILED! ❌")
                print("=============================")
                
        except KeyboardInterrupt:
            logger.info("Demo interrupted by user")
        
        # Cleanup
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            logger.info(f"Removed test file: {test_file_path}")

if __name__ == "__main__":
    main()