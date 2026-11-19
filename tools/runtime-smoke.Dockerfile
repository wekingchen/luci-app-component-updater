# Native ARM64 Linux musl runtime approximating the OpenWrt userspace ABI.
# Build once on the trusted GitHub ARM64 runner; execute upstream binaries
# with no network, no Linux capabilities, and a read-only filesystem.
FROM alpine:3.22
RUN apk add --no-cache libgcc
USER 65534:65534
