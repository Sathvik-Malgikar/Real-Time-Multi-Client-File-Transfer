#!/bin/bash

# Script to run performance and stress tests for the file transfer system
# This script provides more detailed performance metrics and stress testing

echo "===== File Transfer System Performance and Stress Test ====="

# Create test directory
TEST_DIR="perf_test_files"
mkdir -p $TEST_DIR

# Function to generate test files of various sizes
generate_test_files() {
    echo "Generating test files..."
    
    # Generate 1KB file
    dd if=/dev/urandom of="${TEST_DIR}/test_1KB.bin" bs=1K count=1 2>/dev/null
    
    # Generate 10KB file
    dd if=/dev/urandom of="${TEST_DIR}/test_10KB.bin" bs=1K count=10 2>/dev/null
    
    # Generate 1MB file
    dd if=/dev/urandom of="${TEST_DIR}/test_1MB.bin" bs=1M count=1 2>/dev/null
    
    # Generate 10MB file
    dd if=/dev/urandom of="${TEST_DIR}/test_10MB.bin" bs=1M count=10 2>/dev/null
    
    # Generate 100MB file (only if large test flag is set)
    if [ "$1" = "large" ]; then
        echo "Generating 100MB test file..."
        dd if=/dev/urandom of="${TEST_DIR}/test_100MB.bin" bs=1M count=100 2>/dev/null
    fi
    
    echo "Test files generated successfully."
}

# Function to modify error rate in server
modify_server_error_rate() {
    ERROR_RATE=$1
    echo "Setting server error rate to $ERROR_RATE"
    
    # Create temporary server file with modified error rate
    cat server.py | sed "s/ERROR_RATE = 0.2/ERROR_RATE = $ERROR_RATE/" > "${TEST_DIR}/test_server.py"
}

# Function to check file integrity
verify_file_integrity() {
    ORIGINAL_FILE=$1
    RECEIVED_FILE=$2
    
    echo "Verifying file integrity..."
    ORIG_CHECKSUM=$(sha256sum "$ORIGINAL_FILE" | awk '{print $1}')
    RECV_CHECKSUM=$(sha256sum "$RECEIVED_FILE" | awk '{print $1}')
    
    if [ "$ORIG_CHECKSUM" = "$RECV_CHECKSUM" ]; then
        echo "✅ File integrity verified: Checksums match"
        return 0
    else
        echo "❌ File integrity check failed: Checksums do not match"
        echo "Original: $ORIG_CHECKSUM"
        echo "Received: $RECV_CHECKSUM"
        return 1
    fi
}

# Performance test function
run_performance_test() {
    echo
    echo "===== PERFORMANCE TEST ====="
    
    # Start server with low error rate for performance testing
    modify_server_error_rate 0.05
    python "${TEST_DIR}/test_server.py" &
    SERVER_PID=$!
    
    # Wait for server to start
    sleep 2
    
    # Test files of increasing size
    for FILE in "${TEST_DIR}/test_1KB.bin" "${TEST_DIR}/test_10KB.bin" "${TEST_DIR}/test_1MB.bin" "${TEST_DIR}/test_10MB.bin"; do
        FILE_SIZE=$(ls -lh "$FILE" | awk '{print $5}')
        echo
        echo "Testing file: $FILE ($FILE_SIZE)"
        
        # Clean up any previous received files
        RECEIVED_FILE="${FILE%.*}_received.bin"
        [ -f "$RECEIVED_FILE" ] && rm "$RECEIVED_FILE"
        
        # Time the transfer
        START_TIME=$(date +%s.%N)
        python client.py "$FILE"
        END_TIME=$(date +%s.%N)
        
        # Calculate duration and throughput
        DURATION=$(echo "$END_TIME - $START_TIME" | bc)
        FILE_SIZE_BYTES=$(ls -l "$FILE" | awk '{print $5}')
        THROUGHPUT=$(echo "scale=2; $FILE_SIZE_BYTES / $DURATION / 1024 / 1024" | bc)
        
        echo "Transfer time: ${DURATION}s"
        echo "Throughput: ${THROUGHPUT} MB/s"
        
        # Verify file integrity
        verify_file_integrity "$FILE" "$RECEIVED_FILE"
    done
    
    # Clean up
    kill $SERVER_PID
    wait $SERVER_PID 2>/dev/null
}

# Concurrent clients test function
run_concurrent_clients_test() {
    NUM_CLIENTS=$1
    echo
    echo "===== CONCURRENT CLIENTS TEST ($NUM_CLIENTS clients) ====="
    
    # Start server
    modify_server_error_rate 0.2
    python "${TEST_DIR}/test_server.py" &
    SERVER_PID=$!
    
    # Wait for server to start
    sleep 2
    
    # Run multiple clients concurrently
    echo "Starting $NUM_CLIENTS clients simultaneously..."
    for ((i=1; i<=$NUM_CLIENTS; i++)); do
        # Copy test file for each client
        cp "${TEST_DIR}/test_1MB.bin" "${TEST_DIR}/client_${i}_test.bin"
        # Start client in background
        python client.py "${TEST_DIR}/client_${i}_test.bin" > "${TEST_DIR}/client_${i}_output.log" 2>&1 &
        CLIENT_PIDS[$i]=$!
    done
    
    # Wait for all clients to finish
    echo "Waiting for clients to complete..."
    for ((i=1; i<=$NUM_CLIENTS; i++)); do
        wait ${CLIENT_PIDS[$i]}
        echo "Client $i finished"
    done
    
    # Verify all files
    echo "Verifying file integrity for all clients..."
    SUCCESS_COUNT=0
    for ((i=1; i<=$NUM_CLIENTS; i++)); do
        if verify_file_integrity "${TEST_DIR}/client_${i}_test.bin" "${TEST_DIR}/client_${i}_test_received.bin" > /dev/null; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        fi
    done
    
    echo "$SUCCESS_COUNT out of $NUM_CLIENTS transfers completed successfully"
    
    # Clean up
    kill $SERVER_PID
    wait $SERVER_PID 2>/dev/null
}

# Error rate stress test
run_error_rate_test() {
    echo
    echo "===== ERROR RATE STRESS TEST ====="
    
    TEST_FILE="${TEST_DIR}/test_1MB.bin"
    
    # Test increasing error rates
    for RATE in 0.1 0.3 0.5 0.7; do
        echo
        echo "Testing with error rate: $RATE"
        
        # Start server with specific error rate
        modify_server_error_rate $RATE
        python "${TEST_DIR}/test_server.py" &
        SERVER_PID=$!
        
        # Wait for server to start
        sleep 2
        
        # Clean up any previous received files
        RECEIVED_FILE="${TEST_FILE%.*}_received.bin"
        [ -f "$RECEIVED_FILE" ] && rm "$RECEIVED_FILE"
        
        # Time the transfer
        START_TIME=$(date +%s.%N)
        python client.py "$TEST_FILE"
        END_TIME=$(date +%s.%N)
        
        # Calculate duration
        DURATION=$(echo "$END_TIME - $START_TIME" | bc)
        echo "Transfer time with error rate $RATE: ${DURATION}s"
        
        # Verify file integrity
        verify_file_integrity "$TEST_FILE" "$RECEIVED_FILE"
        
        # Clean up
        kill $SERVER_PID
        wait $SERVER_PID 2>/dev/null
    done
}

# Main test execution
main() {
    echo "Starting file transfer system tests..."
    
    # Check if we should run large file tests
    if [ "$1" = "large" ]; then
        LARGE_TEST=true
        echo "Including large file tests (100MB)"
    else
        LARGE_TEST=false
        echo "Skipping large file tests (use 'large' argument to include)"
    fi
    
    # Generate test files
    generate_test_files $1
    
    # Run performance test
    run_performance_test
    
    # Run concurrent clients test with 5 clients
    run_concurrent_clients_test 5
    
    # Run concurrent clients test with 10 clients if large test
    if [ "$LARGE_TEST" = true ]; then
        run_concurrent_clients_test 10
    fi
    
    # Run error rate stress test
    run_error_rate_test
    
    echo
    echo "All tests completed."
    
    # Clean up test directory if all tests pass
    read -p "Clean up test files? (y/n): " CLEANUP
    if [ "$CLEANUP" = "y" ]; then
        echo "Cleaning up test files..."
        rm -rf $TEST_DIR
        echo "Done."
    fi
}

# Run the tests
main $1