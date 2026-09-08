package com.example.orderservice;

import java.time.Instant;

/**
 * Order record — immutable once created. Spec Section 13: no database
 * required for the POC, in-memory only; focus stays on AI orchestration,
 * not this service's own business logic.
 */
public class Order {

    private final String id;
    private final String item;
    private final int quantity;
    private final Instant createdAt;

    public Order(String id, String item, int quantity, Instant createdAt) {
        this.id = id;
        this.item = item;
        this.quantity = quantity;
        this.createdAt = createdAt;
    }

    public String getId() {
        return id;
    }

    public String getItem() {
        return item;
    }

    public int getQuantity() {
        return quantity;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
