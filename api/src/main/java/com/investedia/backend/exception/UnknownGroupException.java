package com.investedia.backend.exception;

import java.util.List;

public class UnknownGroupException extends RuntimeException {
    private final List<String> groups;

    public UnknownGroupException(List<String> groups) {
        super("unknown group");
        this.groups = List.copyOf(groups);
    }

    public List<String> groups() { return groups; }
}
