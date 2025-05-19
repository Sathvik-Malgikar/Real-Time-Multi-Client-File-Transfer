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

## Further Development

Potential areas for future development include:

-   Implementing more sophisticated congestion control mechanisms.
-   Adding security features like encryption.
-   Improving the user interface for the client.