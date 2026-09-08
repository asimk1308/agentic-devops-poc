package com.example.orderservice;

import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.Collection;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * In-memory order store. A real service would have a database and its own
 * failure modes worth investigating; deliberately kept out per Spec
 * Section 13 — this app exists to be monitored and investigated, not to
 * demonstrate persistence.
 */
@Component
public class OrderStore {

    private final Map<String, Order> orders = new ConcurrentHashMap<>();

    public Order create(String item, int quantity) {
        String id = UUID.randomUUID().toString();
        Order order = new Order(id, item, quantity, Instant.now());
        orders.put(id, order);
        return order;
    }

    public Optional<Order> findById(String id) {
        return Optional.ofNullable(orders.get(id));
    }

    public Collection<Order> findAll() {
        return orders.values();
    }
}
