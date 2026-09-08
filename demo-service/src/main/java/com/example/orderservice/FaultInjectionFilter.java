package com.example.orderservice;

import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Spec Section 12 — controlled fault injection for demo Scenarios 2/3
 * (latency regression / error regression), driven entirely by env vars
 * so scripts/inject_latency.sh and scripts/inject_failure.sh can turn a
 * scenario on/off with just a restart, no code change per scenario.
 *
 * Applies to every request (a servlet Filter, not controller code) so
 * the aggregate http_server_requests_seconds_* series Prometheus scrapes
 * reflect it regardless of which endpoint scripts/generate_load.py
 * happens to hit.
 *
 * Deliberately not "randomly return fake JSON" (Section 12's warning
 * against that) -- this is a real Thread.sleep() and a real 5xx
 * response on a real request, so Prometheus really measures degraded
 * latency/error-rate and the log file really gets an ERROR line, same
 * as an actual regression would produce. See docs/learning-notes.md
 * Phase 4 fault-injection notes for what this looked like live.
 */
@Component
public class FaultInjectionFilter implements Filter {

    private static final Logger log = LoggerFactory.getLogger(FaultInjectionFilter.class);

    @Value("${FAULT_LATENCY_MS:0}")
    private long faultLatencyMs;

    @Value("${FAULT_ERROR_RATE:0.0}")
    private double faultErrorRate;

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        if (faultLatencyMs > 0) {
            try {
                Thread.sleep(faultLatencyMs);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }

        if (faultErrorRate > 0.0 && ThreadLocalRandom.current().nextDouble() < faultErrorRate) {
            log.error(
                    "Injected fault: simulated failure processing {} {} (FAULT_ERROR_RATE={})",
                    ((jakarta.servlet.http.HttpServletRequest) request).getMethod(),
                    ((jakarta.servlet.http.HttpServletRequest) request).getRequestURI(),
                    faultErrorRate);
            ((HttpServletResponse) response)
                    .sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR, "Injected fault (FAULT_ERROR_RATE)");
            return;
        }

        chain.doFilter(request, response);
    }
}
