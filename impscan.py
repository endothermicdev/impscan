#!/usr/bin/env python3
from pyln.client import Plugin, RpcError
from enum import Enum

plugin = Plugin()

# Still experimental, not interop tested/approved.
pending_features = {"OPTION_WILL_FUND_FOR_FOOD": 30,
                    "OPTION_INV_GOSSIP": 34,
                    "OPTION_SCHNORR_GOSSIP": 38,
                    "KEYSEND": 54,
                    "TRUSTED_SWAP_IN_PROVIDER": 142}
# Established features from BOLT7
est_features = {"OPTION_DATA_LOSS_PROTECT": 0,
                "INITIAL_ROUTING_SYNC": 2,
                "OPTION_UPFRONT_SHUTDOWN_SCRIPT": 4,
                "OPT_GOSSIP_QUERIES": 6,
                "VAR_ONION_OPTIN": 8,
                "GOSSIP_QUERIES_EX": 10,
                "OPTION_STATIC_REMOTEKEY": 12,
                "PAYMENT_SECRET": 14,
                "BASIC_MPP": 16,
                "OPTION_SUPPORT_LARGE_CHANNEL": 18,
                "OPTION_ANCHOR_OUTPUTS": 20,
                "OPTION_ANCHORS_ZERO_FEE_HTLC_TX": 22,
                "OPTION_SHUTDOWN_ANYSEGWIT": 26,
                "OPT_DUAL_FUND": 28,
                "OPTION_CHANNEL_TYPE": 44,
                "OPTION_SCID_ALIAS": 46,
                "OPTION_PAYMENT_METADATA": 48,
                "OPT_ZEROCONF": 50}

possFeatures = {**pending_features, **est_features}


class feature(Enum):
    MANDATORY = 'mandatory'
    OPTIONAL = 'optional'
    NOT_MANDATORY = 'not mandatory'
    NOT_OPTIONAL = 'not optional'
    NOT_SET = 'not set'


class heuristic(object):
    def __init__(self, implementation_name, **features):
        self.name = implementation_name
        self.features = features

    def testFeature(self, features, bitnumber):
        """Test for mandatory or optional positions."""
        return ((features & (1 << bitnumber)) != 0)

    def test(self, features):
        """Test a features bitfield against this heuristic."""
        assert isinstance(features, int)
        for fname, fvalue in self.features.items():
            if fvalue == feature.MANDATORY:
                if not self.testFeature(features, possFeatures[fname]):
                    return False
            if fvalue == feature.OPTIONAL:
                if not self.testFeature(features, possFeatures[fname]+1):
                    return False
            if fvalue == feature.NOT_MANDATORY:
                if self.testFeature(features, possFeatures[fname]):
                    return False
            if fvalue == feature.NOT_OPTIONAL:
                if self.testFeature(features, possFeatures[fname]):
                    return False
            if fvalue == feature.NOT_SET:
                if self.testFeature(features, possFeatures[fname]) or\
                   self.testFeature(features, possFeatures[fname]+1):
                    return False
        return True


CLN_EXP = heuristic("CLN Experimental",
                    OPT_DUAL_FUND=feature.OPTIONAL,
                    GOSSIP_QUERIES_EX=feature.OPTIONAL)

Eclair = heuristic("Eclair",
                   OPTION_SUPPORT_LARGE_CHANNEL=feature.OPTIONAL,
                   OPTION_ANCHORS_ZERO_FEE_HTLC_TX=feature.OPTIONAL,
                   OPTION_DATA_LOSS_PROTECT=feature.OPTIONAL)

LND = heuristic("LND", OPTION_DATA_LOSS_PROTECT=feature.MANDATORY)

CLN = heuristic("CLN",
                OPTION_DATA_LOSS_PROTECT=feature.OPTIONAL,
                OPTION_STATIC_REMOTEKEY=feature.NOT_MANDATORY,
                GOSSIP_QUERIES_EX=feature.OPTIONAL)

LDK = heuristic("LDK",
                VAR_ONION_OPTIN=feature.MANDATORY)

Unknown = heuristic("2200",
                    VAR_ONION_OPTIN=feature.OPTIONAL,
                    OPTION_STATIC_REMOTEKEY=feature.OPTIONAL)


# heuristics should be ordered from most unique/restrictive features to least
all_heuristics = [CLN_EXP, Eclair, LND, CLN, LDK, Unknown]


def testFeature(features, bitnumber):
    """Test for mandatory or optional positions."""
    assert isinstance(features, int)
    return ((features & (1 << bitnumber)) != 0)


def identifyFingerprint(feat):
    assert isinstance(feat, int)
    for h in all_heuristics:
        if h.test(feat):
            return h.name
    return ("indef")


def unknownFeatures(features):
    known_features = []
    unknown = []
    for k in possFeatures.keys():
        known_features.append(possFeatures[k])
        known_features.append(possFeatures[k]+1)
    for x in range(len(bin(features))-2):
        if (testFeature(features, x) and (x not in known_features)):
            unknown.append(x)
    return unknown


def decodeFeatures(features):
    """pass a feature bit string (HEX) and return a human readable output."""
    assert isinstance(features, str)
    try:
        f = int(features, 16)
    except:
        return (["feature bit decode failed. (hex encoding required)"])
    result = {}
    for k, v in possFeatures.items():
        if testFeature(f, possFeatures[k]+1):
            result.update({"{:<4} {}".format(v+1, k): "optional"})
        elif testFeature(f, possFeatures[k]):
            result.update({"{:<4} {}".format(v, k): "mandatory"})
    uf = unknownFeatures(f)
    if (len(uf) > 0):
        result.update({"Unknown features": uf})
    return result


def queryNodeFeatures(nodeid):
    if (len(str(nodeid)) != 66):
        raise Exception("nodeid must be 33 bytes (66 hex chars)")
    try:
        query = plugin.rpc.listnodes(str(nodeid))
    except RpcError as e:
        if ('code', -32602) in e.error.items():
            return ("Nodeid not found. Invalid token")
        return "Error encountered during call to listnodes: {}".format(e)
    node = query['nodes'][0]
    return node["features"]


def singleNodeDecode(nodeid):
    return decodeFeatures(queryNodeFeatures(nodeid))


def testNodes(test_items):
    """feed a json dict of node_id:heuristic pairs and this will fingerprint
    the nodes and validate that they match the desired heuristic. A list of
    nodes from all implementations will validate that all the heuristics
    remain effective."""
    if not isinstance(test_items, dict):
        return "test argument requires a json dict of format \
'{\"node_id\":\"heuristic\"}'"
    answer = []
    for node, h in test_items.items():
        f = queryNodeFeatures(node)
        if "Error" in f:
            return f
        fingerprint = identifyFingerprint(int(f, 16))
        answer.append({"node_id": node,
                       "features": f,
                       "test heuristic": h,
                       "fingerprint": fingerprint,
                       "status": fingerprint == h})
    return answer


def fullScan():
    """Fingerprint all nodes on the network using all heuristics."""
    heuristic_check = {}
    for h in all_heuristics:
        for f in h.features.keys():
            if f not in possFeatures.keys():
                return {"error": "{} not a possible feature "
                        "({} heuristic)".format(f, h.name)}
    plugin.log("impscan calling listnodes via rpc")
    nodes = plugin.rpc.listnodes()['nodes']
    s = "impscan: listnodes returned {} items".format(len(nodes))
    plugin.log(s)
    c = 0
    result = {}
    for h in all_heuristics:
        result.update({h.name: 0})
    result.update({"indef": 0, "no features": 0})
    indefs = []
    for n in nodes:
        c += 1
        if ("features" not in n):
            result["no features"] += 1
            continue
        if (n["features"] is None or n["features"] == ''):
            result["no features"] += 1
            continue
        r = identifyFingerprint(int(n["features"], 16))
        if r == "indef":
            indefs.append(n)
        result[r] += 1
    t = 0
    for i in result.keys():
        t += result[i]

    return result


@plugin.method("impscan")
def impscan(plugin, **kwargs):
    """Estimate breakdown of various lightning implementations on the network.
    This relies on the listnodes command and feature bits. Work in progress."""
    for k in kwargs.keys():
        if k not in ["node", "features", "test"]:
            return ["unrecognized keyword '{}'".format(k)]
    if ("node" in kwargs.keys()):
        return singleNodeDecode(kwargs["node"])
    if ("features" in kwargs.keys()):
        return decodeFeatures(kwargs["features"])
    if ("test" in kwargs.keys()):
        return testNodes(kwargs["test"])
    # Run analysis on all network nodes
    return fullScan()


@plugin.init()
def init(options, configuration, plugin, **kwargs):
    plugin.log("Plugin impscan.py initialized")


plugin.run()
