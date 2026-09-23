# Text Injection Latency Benchmarks

| Method | Size (chars) | Latency | CPU Usage | Reliability |
|---|---|---|---|---|
| Direct Clipboard Paste | 1,000 | 28ms | < 1% | 99.8% |
| Simulated Keystrokes | 1,000 | 2,150ms | 12% | 94.2% |
| Native Accessibility SetValue | 1,000 | 15ms | < 1% | 91.0% |

Conclusion: Default to Clipboard Paste with prior clipboard state restoration.
