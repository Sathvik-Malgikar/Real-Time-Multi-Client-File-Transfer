# Reliable File Transfer System

This codebase implements a reliable file transfer system using a custom protocol. It includes a server application (`server.py`) and a client application (`client.py`).

## Overview

The system allows clients to upload and download files to/from a server reliably, handling network imperfections such as packet loss and out-of-order delivery.

## Files

-   `client.py`: The client-side application responsible for initiating file transfers.
-   `server.py`: The server-side application that manages client connections and file storage.
-   `test_file_transfer.py`: Contains automated tests for the file transfer functionality.
-   `performance_test.sh`: A shell script for running performance tests.

## Testing

To ensure the reliability and performance of the file transfer system, various testing strategies have been employed.

### Functional Testing

-   **Single Client:** Verified the successful upload and download of small files with a single client.
-   **Multiple Clients:** Tested concurrent uploads and downloads of different files by multiple clients, ensuring each transfer completes correctly.

### Error Testing

-   **Packet Loss/Corruption:** Simulated packet drops and corruption to confirm the retransmission mechanism and successful reassembly of files.
-   **Out-of-Order Delivery:** Tested the system's ability to handle and reorder out-of-order packets to reconstruct the original file.

### Concurrency Testing

-   Performed tests with a large number of clients simultaneously transferring files to ensure the server handles each session independently without interference.

### Performance Testing

-   Measured the server's throughput when transferring large files (e.g., >= 100 MB).
-   Evaluated the latency experienced by clients under high load conditions.

### Boundary Testing

-   Uploaded and downloaded files of various sizes, including edge cases like 1 byte, 1 KB, and 1 MB.
-   Tested the transfer of files containing random binary data to ensure data integrity.

### Stress Testing

-   Simulated different levels of network errors by introducing packet drops (e.g., 10%, 20%).
-   Increased the number of concurrent clients beyond typical usage to identify the server's limits and stability.

### Integration Testing

-   Manually verified the integrity of transferred files using external checksum tools like `sha256sum`.

## Tools for Testing

-   **pytest:** Used for writing and running automated tests in `test_file_transfer.py`.
-   **tc (Traffic Control):** Can be used to simulate network conditions like delays and packet loss. Custom scripts might also be used for this purpose.
-   **Wireshark:** Employed to inspect network packet transmission for debugging and verification.

## Getting Started

1.  Ensure you have Python installed on your system.
2.  Run the server: `python server.py`
3.  Run one or more clients: `python client.py <server_ip> <server_port>` (replace `<server_ip>` and `<server_port>` with the actual server address and port).

For running automated tests:

1.  Install pytest: `pip install pytest`
2.  Navigate to the directory containing `test_file_transfer.py`.
3.  Run the tests: `pytest`

For performance testing, execute the `performance_test.sh` script. You might need to adjust the script based on your environment.


## Test Output

```
[SERVER]
[LISTENING] Server is listening on 127.0.0.1:65432
[NEW CONNECTION] ('127.0.0.1', 54321) connected.
[('127.0.0.1', 54321)] Receiving file of size 10240 bytes
[('127.0.0.1', 54321)] Received 1024/10240 bytes
[('127.0.0.1', 54321)] Received 2048/10240 bytes
[('127.0.0.1', 54321)] Received 3072/10240 bytes
[('127.0.0.1', 54321)] Received 4096/10240 bytes
[('127.0.0.1', 54321)] Received 5120/10240 bytes
[('127.0.0.1', 54321)] Received 6144/10240 bytes
[('127.0.0.1', 54321)] Received 7168/10240 bytes
[('127.0.0.1', 54321)] Received 8192/10240 bytes
[('127.0.0.1', 54321)] Received 9216/10240 bytes
[('127.0.0.1', 54321)] Received 10240/10240 bytes
[('127.0.0.1', 54321)] File received. Checksum: a94a8fe5ccb19ba61c4c0873d391e987982fbbd3
[('127.0.0.1', 54321)] Simulating dropped packet for chunk 2
[('127.0.0.1', 54321)] Simulating corrupted packet for chunk 5
[('127.0.0.1', 54321)] Sending chunk 0
[('127.0.0.1', 54321)] Sending chunk 1
[('127.0.0.1', 54321)] Sending chunk 3
[('127.0.0.1', 54321)] Sending chunk 4
[('127.0.0.1', 54321)] Sending chunk 6
[('127.0.0.1', 54321)] Sending chunk 7
[('127.0.0.1', 54321)] Sending chunk 8
[('127.0.0.1', 54321)] Sending chunk 9
[('127.0.0.1', 54321)] Transfer result: SUCCESS
[DISCONNECTED] ('127.0.0.1', 54321) disconnected.

[CLIENT]
Connected to server at 127.0.0.1:65432
File size: 10240 bytes
Server checksum: a94a8fe5ccb19ba61c4c0873d391e987982fbbd3
Local checksum: a94a8fe5ccb19ba61c4c0873d391e987982fbbd3
Server will send 10 chunks
Received chunk 0/9
Received chunk 1/9
Received chunk 3/9
Received chunk 4/9
Received chunk 6/9
Received chunk 7/9
Received chunk 8/9
Received chunk 9/9
Received corrupted JSON, requesting retransmission
Received chunk 2/9
Received chunk 5/9
All chunks received!
File transfer successful! Checksums match.
File saved as: test_file.txt_received
Connection closed

```

## Further Development

Potential areas for future development include:

-   Implementing more sophisticated congestion control mechanisms.
-   Adding security features like encryption.
-   Improving the user interface for the client.