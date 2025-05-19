import pytest
import socket
import threading
import time
import hashlib
import os
import random
import string
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import unittest
from typing import List, Dict, Any, Tuple, Optional

# Import client and server modules
sys.path.append('.')
try:
    import client
    import server
except ImportError:
    # If they can't be imported, we'll use subprocess to run them
    pass

# Test configuration
TEST_HOST = '127.0.0.1'
TEST_PORT = 65433  # Use a different port for testing
TEST_DIR = "test_files"
TEST_SIZES = [1, 1024, 1024 * 10, 1024 * 100, 1024 * 1000]  # 1B, 1KB, 10KB, 100KB, 1MB

# Utility functions
def generate_random_file(size: int, path: str) -> str:
    """Generate a file with random content of specified size"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(os.urandom(size))
    return path

def calculate_checksum(file_path: str) -> str:
    """Calculate SHA256 checksum of a file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(4096), b''):
            sha256.update(block)
    return sha256.hexdigest()

def run_server(port: int, error_rate: float = 0.2) -> subprocess.Popen:
    """Run server process with specified error rate"""
    # Modify server configuration for testing
    with open('server.py', 'r') as f:
        server_code = f.read()
    
    # Replace port and error rate
    server_code = server_code.replace('PORT = 65432', f'PORT = {port}')
    server_code = server_code.replace('ERROR_RATE = 0.2', f'ERROR_RATE = {error_rate}')
    
    # Write temporary server file
    with open('test_server.py', 'w') as f:
        f.write(server_code)
    
    # Start server process
    return subprocess.Popen([sys.executable, 'test_server.py'])

def run_client(port: int, file_path: str) -> subprocess.Popen:
    """Run client process"""
    # Modify client configuration for testing
    with open('client.py', 'r') as f:
        client_code = f.read()
    
    # Replace port
    client_code = client_code.replace('PORT = 65432', f'PORT = {port}')
    
    # Write temporary client file
    with open('test_client.py', 'w') as f:
        f.write(client_code)
    
    # Start client process
    return subprocess.Popen([sys.executable, 'test_client.py', file_path])

def verify_file_transfer(original_path: str, received_path: str) -> bool:
    """Verify that files have the same content"""
    original_checksum = calculate_checksum(original_path)
    received_checksum = calculate_checksum(received_path)
    return original_checksum == received_checksum

class TestFileTransferSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Create test directory
        os.makedirs(TEST_DIR, exist_ok=True)
        
        # Generate test files of different sizes
        cls.test_files = {}
        for size in TEST_SIZES:
            file_path = os.path.join(TEST_DIR, f"test_{size}bytes.bin")
            generate_random_file(size, file_path)
            cls.test_files[size] = file_path
        
        # Create binary test file
        cls.binary_file = os.path.join(TEST_DIR, "binary_test.bin")
        with open(cls.binary_file, 'wb') as f:
            f.write(os.urandom(1024 * 10))  # 10KB of random binary data
    
    def setUp(self):
        """Set up for each test"""
        # Start server with default error rate
        self.server_process = run_server(TEST_PORT)
        time.sleep(1)  # Give server time to start
    
    def tearDown(self):
        """Clean up after each test"""
        # Terminate server process
        if hasattr(self, 'server_process'):
            self.server_process.terminate()
            self.server_process.wait()
        
        # Clean up received files
        for file_path in list(self.test_files.values()) + [self.binary_file]:
            received_path = file_path.replace('.bin', '_received.bin')
            if os.path.exists(received_path):
                os.remove(received_path)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        # Remove test files
        for file_path in list(cls.test_files.values()) + [cls.binary_file]:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Remove temporary test files
        if os.path.exists('test_server.py'):
            os.remove('test_server.py')
        if os.path.exists('test_client.py'):
            os.remove('test_client.py')
    
    # 1. Functional Testing
    def test_single_client(self):
        """Test with a single client uploading a small file"""
        file_path = self.test_files[1024]  # 1KB file
        
        # Run client
        client_process = run_client(TEST_PORT, file_path)
        client_process.wait()
        
        # Verify transfer
        received_path = file_path.replace('.bin', '_received.bin')
        self.assertTrue(os.path.exists(received_path), "Received file does not exist")
        self.assertTrue(verify_file_transfer(file_path, received_path), "File content doesn't match")
    
    def test_multiple_clients(self):
        """Test with multiple clients uploading different files"""
        # Select test files
        file_paths = [self.test_files[1024], self.test_files[1024 * 10]]
        
        # Run clients
        client_processes = []
        for file_path in file_paths:
            client_process = run_client(TEST_PORT, file_path)
            client_processes.append(client_process)
        
        # Wait for clients to finish
        for process in client_processes:
            process.wait()
        
        # Verify transfers
        for file_path in file_paths:
            received_path = file_path.replace('.bin', '_received.bin')
            self.assertTrue(os.path.exists(received_path), f"Received file {received_path} does not exist")
            self.assertTrue(verify_file_transfer(file_path, received_path), f"File content doesn't match for {file_path}")
    
    # 2. Error Testing
    def test_high_error_rate(self):
        """Test with high error rate to ensure retransmissions work"""
        # Stop default server
        self.server_process.terminate()
        self.server_process.wait()
        
        # Start server with high error rate
        self.server_process = run_server(TEST_PORT, error_rate=0.5)
        time.sleep(1)
        
        # Upload file
        file_path = self.test_files[1024 * 10]  # 10KB file
        client_process = run_client(TEST_PORT, file_path)
        client_process.wait()
        
        # Verify transfer
        received_path = file_path.replace('.bin', '_received.bin')
        self.assertTrue(os.path.exists(received_path), "Received file does not exist")
        self.assertTrue(verify_file_transfer(file_path, received_path), "File content doesn't match")
    
    # 3. Concurrency Testing
    def test_many_concurrent_clients(self):
        """Test with a large number of concurrent clients"""
        # Use multiple small files
        file_path = self.test_files[1024]  # 1KB file
        num_clients = 10
        
        # Run clients concurrently
        client_processes = []
        for i in range(num_clients):
            # Create a copy of the test file for each client
            client_file = os.path.join(TEST_DIR, f"client_{i}_test.bin")
            with open(file_path, 'rb') as src, open(client_file, 'wb') as dst:
                dst.write(src.read())
            
            # Run client
            client_process = run_client(TEST_PORT, client_file)
            client_processes.append((client_process, client_file))
        
        # Wait for clients to finish
        for process, _ in client_processes:
            process.wait()
        
        # Verify transfers
        for _, client_file in client_processes:
            received_path = client_file.replace('.bin', '_received.bin')
            self.assertTrue(os.path.exists(received_path), f"Received file {received_path} does not exist")
            self.assertTrue(verify_file_transfer(client_file, received_path), f"File content doesn't match for {client_file}")
            
            # Clean up
            os.remove(client_file)
            os.remove(received_path)
    
    # 4. Performance Testing
    def test_large_file_performance(self):
        """Test performance with a large file"""
        # Only run if not in CI environment to avoid long tests
        if os.environ.get('CI') == 'true':
            self.skipTest("Skipping large file test in CI environment")
        
        # Create large test file (5MB for quick testing, can be increased)
        large_file = os.path.join(TEST_DIR, "large_test.bin")
        generate_random_file(5 * 1024 * 1024, large_file)
        
        # Measure transfer time
        start_time = time.time()
        client_process = run_client(TEST_PORT, large_file)
        client_process.wait()
        end_time = time.time()
        
        # Calculate throughput
        file_size_mb = os.path.getsize(large_file) / (1024 * 1024)
        transfer_time = end_time - start_time
        throughput = file_size_mb / transfer_time
        
        print(f"\nLarge file transfer: {file_size_mb:.2f} MB in {transfer_time:.2f} seconds")
        print(f"Throughput: {throughput:.2f} MB/s")
        
        # Verify transfer
        received_path = large_file.replace('.bin', '_received.bin')
        self.assertTrue(os.path.exists(received_path), "Received file does not exist")
        self.assertTrue(verify_file_transfer(large_file, received_path), "File content doesn't match")
        
        # Clean up
        os.remove(large_file)
        os.remove(received_path)
    
    # 5. Boundary Testing
    def test_various_file_sizes(self):
        """Test with files of varying sizes"""
        for size, file_path in self.test_files.items():
            # Run client for each file size
            client_process = run_client(TEST_PORT, file_path)
            client_process.wait()
            
            # Verify transfer
            received_path = file_path.replace('.bin', '_received.bin')
            self.assertTrue(os.path.exists(received_path), f"Received file for size {size} does not exist")
            self.assertTrue(verify_file_transfer(file_path, received_path), f"File content doesn't match for size {size}")
            
            # Clean up
            if os.path.exists(received_path):
                os.remove(received_path)
    
    def test_binary_data(self):
        """Test with binary data file"""
        client_process = run_client(TEST_PORT, self.binary_file)
        client_process.wait()
        
        # Verify transfer
        received_path = self.binary_file.replace('.bin', '_received.bin')
        self.assertTrue(os.path.exists(received_path), "Received binary file does not exist")
        self.assertTrue(verify_file_transfer(self.binary_file, received_path), "Binary file content doesn't match")
    
    # 6. Stress Testing
    def test_varying_error_rates(self):
        """Test with different error rates"""
        file_path = self.test_files[1024 * 10]  # 10KB file
        error_rates = [0.1, 0.3, 0.5]
        
        for rate in error_rates:
            # Restart server with new error rate
            if hasattr(self, 'server_process'):
                self.server_process.terminate()
                self.server_process.wait()
            
            self.server_process = run_server(TEST_PORT, error_rate=rate)
            time.sleep(1)
            
            # Run client
            client_process = run_client(TEST_PORT, file_path)
            client_process.wait()
            
            # Verify transfer
            received_path = file_path.replace('.bin', '_received.bin')
            self.assertTrue(os.path.exists(received_path), f"Received file with error rate {rate} does not exist")
            self.assertTrue(verify_file_transfer(file_path, received_path), f"File content doesn't match with error rate {rate}")
            
            # Clean up
            if os.path.exists(received_path):
                os.remove(received_path)
    
    # 7. Integration Testing
    def test_external_checksum_verification(self):
        """Verify file integrity using external tools"""
        file_path = self.test_files[1024]  # 1KB file
        
        # Run client
        client_process = run_client(TEST_PORT, file_path)
        client_process.wait()
        
        # Get received file path
        received_path = file_path.replace('.bin', '_received.bin')
        
        # Calculate checksums using system tools if available
        try:
            original_sum = subprocess.check_output(['sha256sum', file_path]).decode().split()[0]
            received_sum = subprocess.check_output(['sha256sum', received_path]).decode().split()[0]
            self.assertEqual(original_sum, received_sum, "External checksum verification failed")
        except (subprocess.SubprocessError, FileNotFoundError):
            # Fall back to Python implementation if sha256sum not available
            self.assertTrue(verify_file_transfer(file_path, received_path), "Internal checksum verification failed")


if __name__ == "__main__":
    unittest.main()