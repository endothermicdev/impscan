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
lightning-cli impscan features=<hex encoded features>
```

To list the features of a specific nodeid:
```bash
lightning-cli impscan node=<nodeid>
```

To test nodes against their intended implementation heuristic:
```bash
lightning-cli impscan test='{"<node_id>":"<heuristic name>"}'
```
i.e.,
```bash
$ lightning-cli impscan test='{"02df5ffe895c778e10f7742a6c5b8a0cefbe9465df58b92fadeb883752c8107c8f":"CLN"}'
[
   {
      "node_id": "02df5ffe895c778e10f7742a6c5b8a0cefbe9465df58b92fadeb883752c8107c8f",
      "features": "800000080a6aa2",
      "test heuristic": "CLN",
      "fingerprint": "CLN",
      "status": true
   }
]
```

Future work:
 - Add storage to document changes in network implementation usage over time.
