# Real-Time File Transfer and Verification System

A Python-based client-server file transfer system with checksums for integrity verification.

## Overview

This project implements a real-time file transfer system with a focus on data integrity. It features:

- **Client-Server Architecture**: Using TCP sockets for reliable communication
- **File Chunking**: Breaking files into fixed-size chunks for efficient transfer
- **Sequence Numbering**: Handling out-of-order packet delivery
- **Checksum Verification**: Using SHA-256 to ensure file integrity
- **Error Simulation**: Optional simulation of network issues (packet loss, corruption)
- **Automatic Retries**: Recovery mechanisms for failed transfers

## Components

The system consists of three Python files:

1. **server.py** - The server-side application that receives files and sends them back in chunks
2. **client.py** - The client-side application that uploads files and reassembles received chunks
3. **demo.py** - A utility script to demonstrate and test the system

## Requirements

- Python 3.6+
- Standard library modules only (no external dependencies)

## Installation

Clone the repository or download the source files:

```bash
git clone https://github.com/yourusername/file-transfer-system.git
cd file-transfer-system
```

## Usage

### Demo Mode (Recommended for Testing)

Run a complete demonstration with both server and client:

```bash
python demo.py
```

This will:
- Create a test file with random data
- Start the server in a background thread
- Connect a client to the server
- Transfer the file and verify its integrity
- Show the results

Options:
```bash
python demo.py --test-file-size 100 --simulate-errors --error-rate 0.2
```

### Server Mode

Run only the server component:

```bash
python demo.py --mode server
```

Or directly:

```bash
python server.py
```

Options:
- `--host`: Server hostname/IP (default: localhost)
- `--port`: Server port (default: 9999)
- `--chunk-size`: Size of file chunks in bytes (default: 1024)
- `--simulate-errors`: Enable error simulation
- `--error-rate`: Probability of errors (default: 0.1)

### Client Mode

Run only the client component:

```bash
python demo.py --mode client --file path/to/your/file.txt
```

Or directly:

```bash
python client.py
```

Options:
- `--host`: Server hostname/IP (default: localhost)
- `--port`: Server port (default: 9999)
- `--max-retries`: Maximum retry attempts (default: 3)

## Technical Details

### File Transfer Process

1. **File Upload**: Client sends the entire file to the server
2. **Checksum Calculation**: Server computes SHA-256 checksum of uploaded file
3. **File Splitting**: Server divides file into chunks of fixed size (default: 1024 bytes)
4. **Metadata Transfer**: Server sends file metadata including checksum to client
5. **Chunk Transfer**: Server sends chunks (potentially out of order, with simulated errors)
6. **File Reassembly**: Client reassembles chunks in correct order based on sequence numbers
7. **Integrity Verification**: Client verifies file integrity by comparing checksums
8. **Retry Mechanism**: If verification fails, client retries the transfer

### Error Simulation

The system can simulate network issues:

- **Packet Loss**: Randomly skips sending certain chunks
- **Data Corruption**: Randomly flips bits in chunk data
- **Out-of-Order Delivery**: Shuffles the order of chunk transmission

### Communication Protocol

The client-server communication uses JSON messages over TCP sockets:

1. **Message Framing**: Each message is prefixed with its length (4 bytes)
2. **JSON Encoding**: All messages are encoded as JSON objects
3. **Binary Data Handling**: Binary data is encoded/decoded using hexadecimal representation

### Checksum Verification

SHA-256 is used for file integrity verification:

- The server calculates the checksum of the original file
- The client calculates the checksum of the reassembled file
- If checksums match, the transfer is considered successful

## Example Log Output

```
2023-05-16 14:30:25 - FileTransferDemo - INFO - Starting demo mode...
2023-05-16 14:30:25 - FileTransferDemo - INFO - Created test file: /tmp/test_file.dat (10 KB)
2023-05-16 14:30:25 - FileTransferServer - INFO - Server started on localhost:9999
2023-05-16 14:30:26 - FileTransferClient - INFO - Connected to server at localhost:9999
2023-05-16 14:30:26 - FileTransferServer - INFO - Connection established with ('127.0.0.1', 52431)
2023-05-16 14:30:26 - FileTransferServer - INFO - File received and saved as server_test_file.dat
2023-05-16 14:30:26 - FileTransferServer - INFO - Calculated checksum: 6d4a9e7a5e8b3c2f1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0
2023-05-16 14:30:26 - FileTransferServer - INFO - File split into 10 chunks
2023-05-16 14:30:26 - FileTransferServer - INFO - Simulating packet loss for chunk 3
2023-05-16 14:30:26 - FileTransferServer - INFO - Simulating data corruption for chunk 7
2023-05-16 14:30:26 - FileTransferClient - INFO - Original file checksum: 6d4a9e7a5e8b3c2f1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0
2023-05-16 14:30:26 - FileTransferClient - INFO - Server checksum: 6d4a9e7a5e8b3c2f1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0
2023-05-16 14:30:26 - FileTransferClient - INFO - Expected chunks: 10
2023-05-16 14:30:26 - FileTransferClient - INFO - End of transmission received
2023-05-16 14:30:26 - FileTransferClient - ERROR - Missing chunks: received 9 out of 10
2023-05-16 14:30:26 - FileTransferClient - ERROR - Missing sequence numbers: [3]
2023-05-16 14:30:26 - FileTransferClient - INFO - Retrying upload (attempt 1/3)...
...
2023-05-16 14:30:27 - FileTransferClient - INFO - File saved to received_test_file.dat
2023-05-16 14:30:27 - FileTransferClient - INFO - Reassembled file checksum: 6d4a9e7a5e8b3c2f1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0
2023-05-16 14:30:27 - FileTransferClient - INFO - Checksum verification successful!
2023-05-16 14:30:27 - FileTransferClient - INFO - Transfer Successful! Time taken: 1.23 seconds

=================================
🎉 FILE TRANSFER SUCCESSFUL! 🎉
=================================

Original file: /tmp/test_file.dat
Size: 10240 bytes

Received file: received_test_file.dat
Size: 10240 bytes

File sizes match ✅
```

## Error Handling

The system includes several error-handling mechanisms:

1. **Missing Chunks**: If chunks are missing after transmission, the transfer is retried
2. **Checksum Mismatch**: If the reassembled file doesn't match the original checksum, the transfer is retried
3. **Connection Errors**: Handles disconnections and network issues
4. **Retry Limits**: Configurable maximum retry attempts before giving up

## Extensions and Future Work

Potential enhancements:

- **Compression**: Implement data compression to reduce transfer size
- **Encryption**: Add end-to-end encryption for secure transfers
- **Partial Transfers**: Support resuming interrupted transfers
- **Multiple File Support**: Handle batch transfers of multiple files
- **Progress Reporting**: Add real-time progress indicators
- **GUI Interface**: Develop a graphical user interface
- **Forward Error Correction**: Add FEC codes for more robust transfers

## License

[MIT License](LICENSE)

## Author

Your Name

## Acknowledgments

- This project was created as a programming exercise
- Inspired by real-world file transfer protocols
