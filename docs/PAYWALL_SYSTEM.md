# Atlas Paywall Handling System

## Overview
Integrated system for detecting and optionally bypassing paywalls with multiple verification layers and legal safeguards.

**Enhanced with insights from:**
- [RemovePaywalls.com](https://removepaywalls.com/blog/) - Site-specific techniques and bypass strategies
- [magnolia1234/bypass-paywalls-clean](https://gitflic.ru/project/magnolia1234/bypass-paywalls-clean-filters) - Filter-based implementation methods

**See [PAYWALL_DETECTION_GUIDE.md](PAYWALL_DETECTION_GUIDE.md) for detailed site-specific implementation patterns.**

---

## Detection System

### 1. DOM Element Detection
```python
# Example: Checking for common paywall elements
PAYWALL_ELEMENTS = {
    "overlays": [".paywall-overlay", "paywall"],
    "modals": ["subscription-modal", "gateway-content"],
    "banners": ["subscribe-banner", "metered-content"]
}
```

### 2. URL Pattern Matching
```python
PAYWALL_URL_INDICATORS = [
    r"subscribe",
    r"paywall=true",
    r"metered",
    r"premium"
]
```

### 3. Content Analysis
```python
PAYWALL_PHRASES = [
    "subscribe to continue reading",
    "you've reached your article limit",
    "this content is for subscribers only"
]
```

### 4. Network Request Monitoring
- Blocks requests to known paywall endpoints
- Analyzes response headers for paywall indicators

---

## Bypass System (Disabled by Default)

### Legal Compliance Framework
```yaml
# config/paywall_config.yaml
paywall_bypass:
  enabled: false  # Must be explicitly enabled per-domain
  allowed_domains: []
  consent_requirements:
    user_consent: required
    logging: required
    audit_trail: required
  methods:
    dom_cleanup: true
    cookie_reset: false
    header_spoofing: false
```

### Implementation Layers
1. **DOM Cleanup** - Removes overlay elements
2. **Cookie Management** - Resets meter counts
3. **Header Spoofing** - Simulates search engine traffic
4. **Archive Fallback** - Attempts archive.org/archive.is

---

## Integration Guide

### Enabling for Development
```python
from helpers.paywall import PaywallSystem

# Initialize with strict legal safeguards
paywall = PaywallSystem(
    enabled=False,
    log_file="paywall_access.log",
    require_consent=True
)

# Enable selectively for testing
paywall.enable_for_domain(
    domain="nytimes.com",
    methods=["dom_cleanup"],
    consent_reason="Testing purposes"
)
```

### Testing Protocol
```bash
python -m pytest tests/paywall/ \
  --test-domains=nytimes.com,wsj.com \
  --legal-review \
  --audit-log=paywall_test.log
```

---

## Maintenance Procedures

### Weekly Updates
1. Pull latest patterns from [BypassPaywallsClean](https://gitflic.ru/project/magnolia1234/bypass-paywalls-clean-filters)
2. Validate against test suite
3. Update pattern database

### Monitoring Requirements
- Success/failure rates per domain
- False positive tracking
- Monthly legal compliance audits

---

## Frequently Encountered Paywalls

| Domain         | Detection Signs                  | Working Bypass Methods       | Legal Status  |
|----------------|-----------------------------------|-------------------------------|---------------|
| nytimes.com    | CSS selectors, cookie            | Header spoofing              | High risk     |
| wsj.com        | URL pattern, meter count         | Archive access               | Medium risk   |
| medium.com     | JavaScript paywall               | DOM cleanup                  | Low risk      |
| bloomberg.com  | Overlay + subscription nag       | Cookie reset                 | High risk     |

---

## Legal Safeguards
1. **No Automatic Bypass** - Always disabled by default
2. **Explicit Consent** - Per-domain opt-in required
3. **Comprehensive Logging** - All attempts recorded
4. **Audit Trail** - Reversible actions with timestamps
5. **Emergency Disable** - Instant shutdown capability 