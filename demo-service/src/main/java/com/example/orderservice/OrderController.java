package com.example.orderservice;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Collection;

/**
 * Spec Section 13 — the "real application" the AI agent investigates.
 * Endpoints: POST /orders, GET /orders/{id}, GET /orders. Every request
 * here is what generates the HTTP metrics (count, latency, errors) the
 * observability MCP server (Phase 3) will read via Prometheus.
 */
@RestController
@RequestMapping("/orders")
public class OrderController {

    private final OrderStore orderStore;

    public OrderController(OrderStore orderStore) {
        this.orderStore = orderStore;
    }

    @PostMapping
    public ResponseEntity<Order> createOrder(@RequestBody OrderRequest request) {
        Order order = orderStore.create(request.getItem(), request.getQuantity());
        return ResponseEntity.status(HttpStatus.CREATED).body(order);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Order> getOrder(@PathVariable String id) {
        return orderStore.findById(id)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @GetMapping
    public Collection<Order> listOrders() {
        return orderStore.findAll();
    }
}
