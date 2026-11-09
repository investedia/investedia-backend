package com.investedia.backend.exception;

public class SnapshotUnavailableException extends RuntimeException {
    public SnapshotUnavailableException() {
        super("Saved data is unavailable");
    }
}
