# Corporate VPN & Proxy SSL Handling

In restricted enterprise environments, MITM security certificates (Zscaler, Netskope) trigger `SSLCertVerificationError`.
OmniAssist configures:
- `OMNIASSIST_SSL_VERIFY=0` for dev/intranet bypass.
- Custom CA bundle support via `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE`.
