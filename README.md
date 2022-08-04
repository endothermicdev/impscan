# Network Implementation Scanning Plugin

This plugin estimates the numbers of certain lightning implementations active on
the network.  It relies on the `feature_bits` field of node announcements and
applies simple heuristics to guess which implementation is in use.  As features
are continuously added or removed from implementations, these heuristics are apt
to break and should be routinely updated to match current and past
implementation details.

usage is as follows:
To estimate the implementation breakdown of the whole network:
```bash
lightning-cli impscan
```

To decode a particular feature_bit field:
```bash
lightning-cli features=<hex encoded features>
```

To list the features of a specific nodeid:
```bash
lightning-cli node=<nodeid>
```

Future work:
 - Implement a test to verify correct identification of specific known nodes.
 - Add storage to document changes in network implementation usage over time.
