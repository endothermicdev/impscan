#!/usr/bin/env python3
from enum import Enum
from typing import Union
import random
from pyln.client import Plugin, RpcError

plugin = Plugin()

# Still experimental, not interop tested/approved.
pending_features = {"OPTION_WILL_FUND_FOR_FOOD": 30,
                    "OPTION_QUIESCE": 34,
                    "CLN_WANT_PEER_STORAGE": 40,
                    "CLN_PROVIDE_PEER_STORAGE": 42,
                    "KEYSEND": 54,
                    "OPTION_TRAMPOLINE_ROUTING": 56,
                    "OPTION_SPLICE": 60,
                    "OPTION_SIMPLIFIED_UPDATE": 106,
                    "TRUSTED_SWAP_IN_PROVIDER": 142,
                    "TRUSTED_BACKUP_CLIENT": 144,
                    "TRUSTED_BACKUP_PROVIDER": 146,
                    "OPTION_EXPERIMENTAL_SPLICE": 160,
                    "LSPS0_CONFORMANCE": 728
                    }

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
                "OPTION_ROUTE_BLINDING": 24,
                "OPTION_SHUTDOWN_ANYSEGWIT": 26,
                "OPT_DUAL_FUND": 28,
                "OPTION_ONION_MESSAGES": 38,
                "OPTION_CHANNEL_TYPE": 44,
                "OPTION_SCID_ALIAS": 46,
                "OPTION_PAYMENT_METADATA": 48,
                "OPT_ZEROCONF": 50}

possFeatures = {**pending_features, **est_features}


class Feature(Enum):
    """Describes a particular feature bit requirement for a heuristic"""
    SET = 'optional or mandatory'
    MANDATORY = 'mandatory'
    OPTIONAL = 'optional'
    NOT_MANDATORY = 'not mandatory'
    NOT_OPTIONAL = 'not optional'
    NOT_SET = 'not set'


class Heuristic():
    """A set of features and flagging used to fingerprint a
    lightning node to a certain implementation."""
    def __init__(self, implementation_name: str, **features: Feature):
        self.name = implementation_name
        self.features = features

    def test_feature(self, features: int, bitnumber: int) -> bool:
        """Test for mandatory or optional positions."""
        return (features & (1 << bitnumber)) != 0

    def test(self, features: int):
        """Test a features bitfield against this heuristic."""
        assert isinstance(features, int)
        for fname, fvalue in self.features.items():
            if fvalue == Feature.MANDATORY:
                if not self.test_feature(features, possFeatures[fname]):
                    return False
            if fvalue == Feature.OPTIONAL:
                if not self.test_feature(features, possFeatures[fname]+1):
                    return False
            if fvalue == Feature.NOT_MANDATORY:
                if self.test_feature(features, possFeatures[fname]):
                    return False
            if fvalue == Feature.NOT_OPTIONAL:
                if self.test_feature(features, possFeatures[fname]):
                    return False
            if fvalue == Feature.NOT_SET:
                if self.test_feature(features, possFeatures[fname]) or\
                   self.test_feature(features, possFeatures[fname]+1):
                    return False
        return True


NO_ANYSEGWIT = Heuristic("No OPTION_SHUTDOWN_ANYSEGWIT",
                         OPTION_SHUTDOWN_ANYSEGWIT=Feature.NOT_SET)

CLN_DF_NEW = Heuristic("CLN v23.02+ Dual-Fund",
                       OPT_DUAL_FUND=Feature.OPTIONAL,
                       OPTION_ROUTE_BLINDING=Feature.OPTIONAL,
                       OPTION_DATA_LOSS_PROTECT=Feature.OPTIONAL,
                       OPTION_STATIC_REMOTEKEY=Feature.NOT_MANDATORY,
                       GOSSIP_QUERIES_EX=Feature.OPTIONAL)

CLN_DF_OLD = Heuristic("CLN Broken Dual-Fund",
                       OPT_DUAL_FUND=Feature.OPTIONAL,
                       OPTION_DATA_LOSS_PROTECT=Feature.OPTIONAL,
                       OPTION_STATIC_REMOTEKEY=Feature.NOT_MANDATORY,
                       GOSSIP_QUERIES_EX=Feature.OPTIONAL,
                       KEYSEND=Feature.OPTIONAL)

CLN_24_02 = Heuristic("CLN v24.02+",
                      OPTION_DATA_LOSS_PROTECT=Feature.MANDATORY,
                      OPT_GOSSIP_QUERIES=Feature.SET,
                      OPTION_STATIC_REMOTEKEY=Feature.SET,
                      GOSSIP_QUERIES_EX=Feature.OPTIONAL,
                      KEYSEND=Feature.OPTIONAL,
                      OPTION_ANCHORS_ZERO_FEE_HTLC_TX=Feature.OPTIONAL,
                      OPTION_ROUTE_BLINDING=Feature.OPTIONAL,
                      OPTION_WILL_FUND_FOR_FOOD=Feature.NOT_SET)

CLN_25_05 = Heuristic("CLN v25.05+",
                      OPTION_DATA_LOSS_PROTECT=Feature.MANDATORY,
                      OPT_GOSSIP_QUERIES=Feature.SET,
                      OPTION_STATIC_REMOTEKEY=Feature.SET,
                      GOSSIP_QUERIES_EX=Feature.OPTIONAL,
                      KEYSEND=Feature.OPTIONAL,
                      OPTION_ANCHORS_ZERO_FEE_HTLC_TX=Feature.OPTIONAL,
                      OPTION_ROUTE_BLINDING=Feature.OPTIONAL,
                      OPTION_WILL_FUND_FOR_FOOD=Feature.NOT_SET,
                      CLN_WANT_PEER_STORAGE=Feature.NOT_SET,
                      CLN_PROVIDE_PEER_STORAGE=Feature.OPTIONAL)

Eclair = Heuristic("Eclair",
                   OPTION_DATA_LOSS_PROTECT=Feature.SET,
                   OPTION_STATIC_REMOTEKEY=Feature.OPTIONAL,
                   OPTION_SUPPORT_LARGE_CHANNEL=Feature.OPTIONAL,
                   OPTION_ANCHORS_ZERO_FEE_HTLC_TX=Feature.OPTIONAL,
                   OPTION_WILL_FUND_FOR_FOOD=Feature.NOT_SET)

LND = Heuristic("LND",
                OPTION_WILL_FUND_FOR_FOOD=Feature.OPTIONAL,
                OPTION_DATA_LOSS_PROTECT=Feature.MANDATORY)

CLN = Heuristic("CLN",
                OPTION_DATA_LOSS_PROTECT=Feature.OPTIONAL,
                OPTION_UPFRONT_SHUTDOWN_SCRIPT=Feature.OPTIONAL,
                OPTION_STATIC_REMOTEKEY=Feature.SET,
                GOSSIP_QUERIES_EX=Feature.OPTIONAL,
                KEYSEND=Feature.OPTIONAL,
                OPTION_WILL_FUND_FOR_FOOD=Feature.NOT_SET)

LDK = Heuristic("LDK",
                OPTION_DATA_LOSS_PROTECT=Feature.MANDATORY,
                VAR_ONION_OPTIN=Feature.MANDATORY,
                OPTION_STATIC_REMOTEKEY=Feature.MANDATORY)

Electrum = Heuristic("Electrum",
                     OPTION_DATA_LOSS_PROTECT=Feature.OPTIONAL,
                     OPTION_UPFRONT_SHUTDOWN_SCRIPT=Feature.NOT_SET,
                     OPT_ZEROCONF=Feature.NOT_SET,
                     OPTION_WILL_FUND_FOR_FOOD=Feature.NOT_SET)

nlightning = Heuristic("nlightning",
                       VAR_ONION_OPTIN=Feature.OPTIONAL,
                       INITIAL_ROUTING_SYNC=Feature.MANDATORY)

Unknown = Heuristic("2200",
                    VAR_ONION_OPTIN=Feature.OPTIONAL,
                    OPTION_STATIC_REMOTEKEY=Feature.OPTIONAL)


# heuristics should be ordered from most unique/restrictive features to least
all_heuristics = [nlightning, NO_ANYSEGWIT, LND, CLN_DF_NEW, CLN_DF_OLD,
                  CLN_25_05, CLN_24_02, Eclair, CLN, LDK, Electrum, Unknown]

heuristic_sets = {"CLN": [CLN_DF_NEW, CLN_DF_OLD, CLN_24_02, CLN_25_05, CLN],
                  "Unknown": [NO_ANYSEGWIT, Unknown]}


class MissingNode(Exception):
    """node_id was not found by lightningd"""


class ListNodesException(Exception):
    """listnodes rpc failure"""


def test_feature(features: int, bitnumber: int):
    """Test for mandatory or optional positions."""
    assert isinstance(features, int)
    return (features & (1 << bitnumber)) != 0


def identify_fingerprint(feat: int):
    """tests the given feature bits against each heuristic in order until
    a match is found"""
    assert isinstance(feat, int)
    for heuristic in all_heuristics:
        if heuristic.test(feat):
            return heuristic.name
    return "indef"


def unknown_features(features: int) -> list:
    """Returns a list of any features that are undocumented."""
    known_features = []
    unknown = []
    for _, feat_num in possFeatures.items():
        known_features.append(feat_num)
        known_features.append(feat_num+1)
    for bit in range(len(bin(features))-2):
        if (test_feature(features, bit) and (bit not in known_features)):
            unknown.append(bit)
    return unknown


def decode_features(features: str) -> Union[dict, str]:
    """Pass a feature bit string (HEX) and return a human readable output."""
    assert isinstance(features, str)
    try:
        f = int(features, 16)
    except ValueError:
        return "feature bit decode failed. (hex encoding required)"
    result = {}
    for name, feat_num in possFeatures.items():
        if test_feature(f, feat_num+1):
            result.update({"{:<4} {}".format(feat_num+1, name): "optional"})
        elif test_feature(f, feat_num):
            result.update({"{:<4} {}".format(feat_num, name): "mandatory"})
    if unknown_features(f):
        result.update({"Unknown features": unknown_features(f)})
    if len(unknown_features(f)) > 20:
        return ("excessive unknown features while decoding feature bits "
                f"string {features}")
    return result


def query_node_features(nodeid: str) -> str:
    """return featurebits (hex encoded) for a single node"""
    if len(str(nodeid)) != 66:
        raise Exception("nodeid must be 33 bytes (66 hex chars)")
    try:
        query = plugin.rpc.listnodes(str(nodeid))
    except RpcError as err:
        if ('code', -32602) in err.error.items():
            raise MissingNode(f"node_id {nodeid} not found") from err
        raise ListNodesException(("Error encountered during call to "
                                  f"listnodes: {err}")) from err
    if len(query['nodes']) == 0:
        raise MissingNode(f"node_id {nodeid} not found")
    node = query['nodes'][0]
    return node["features"]


def single_node_decode(nodeid: str) -> Union[list, str]:
    """Find out about a node's feature set and implementation guess"""
    try:
        node_features = query_node_features(nodeid)
    except MissingNode:
        return f'node_id {nodeid} not found'
    return [decode_features(node_features),
            identify_fingerprint(int(node_features, 16))]


def test_nodes(test_items: dict) -> list:
    """feed a json dict of node_id:heuristic pairs and this will fingerprint
    the nodes and validate that they match the desired heuristic. A list of
    nodes from all implementations will validate that all the heuristics
    remain effective."""
    if not isinstance(test_items, dict):
        return "test argument requires a json dict of format \
'{\"node_id\":\"heuristic\"}'"
    answer = []
    for node, test_heur in test_items.items():
        feats = query_node_features(node)
        fingerprint = identify_fingerprint(int(feats, 16))
        answer.append({"node_id": node,
                       "features": feats,
                       "test heuristic": test_heur,
                       "fingerprint": fingerprint,
                       "status": fingerprint == test_heur})
    return answer


def full_scan() -> dict:
    """Fingerprint all nodes on the network using all heuristics."""
    for heuristic in all_heuristics:
        for feature in heuristic.features.keys():
            if feature not in possFeatures.keys():
                return {"error": f"{feature} not a possible feature "
                        f"({heuristic.name} heuristic)"}
    nodes = plugin.rpc.listnodes()['nodes']
    plugin.log(f"listnodes returned {len(nodes)} items")
    tally = {}
    for heuristic in all_heuristics:
        tally.update({heuristic.name: 0})
    tally.update({"indef": 0, "no features": 0, "total": 0})
    indefs = []

    for node in nodes:
        if "features" not in node:
            continue
        if node["features"] is None or node["features"] == '':
            tally["no features"] += 1
            continue
        fingerprint = identify_fingerprint(int(node["features"], 16))
        if fingerprint == "indef":
            indefs.append(node)
        tally[fingerprint] += 1
        tally["total"] += 1

    categorized_tally = {}
    for cat, heuristics in heuristic_sets.items():
        category = {}
        for heuristic in heuristics:
            if heuristic.name not in tally.keys():
                category.update({heuristic.name: 0})
            else:
                category.update({heuristic.name: tally.pop(heuristic.name)})
        categorized_tally.update({cat: category})
    categorized_tally.update(tally)
    return categorized_tally


def sample(heuristic: str, count: str):
    """return the first <count> random nodes matching <heuristic>"""
    if count:
        count = int(count)
    else:
        count = 1
    if heuristic not in [h.name for h in all_heuristics]:
        return f"{heuristic} is not a registered heurisitic"
    nodes = plugin.rpc.listnodes()['nodes']
    random.shuffle(nodes)
    found = []
    for node in nodes:
        if "features" not in node:
            continue
        if node["features"] is None or node["features"] == '':
            continue
        fingerprint = identify_fingerprint(int(node["features"], 16))
        if fingerprint == heuristic:
            found.append(node)
        if len(found) >= count:
            break
    if found:
        return found
    return f'no nodes found matching heuristic {heuristic}'


def infer_usage(arg: str) -> Union[dict, str]:
    """User did not provide explicit call. See if we can do the
    right thing anyway."""
    if len(arg) == 66:
        return single_node_decode(arg)
    maybe_features = decode_features(arg)
    if 'failed' in maybe_features:
        return f'could not infer usage of {arg}'
    return maybe_features


def command_validation(args: list, kwargs: dict):
    """Validate commands and syntax. Return an appropriate error string
    if necessary."""
    assert isinstance(args, (tuple, type(None)))
    assert isinstance(kwargs, (dict, type(None)))
    possible_arguments = ["node", "features", "test", "sample", "count"]
    for cmd, string in kwargs.items():
        if cmd not in possible_arguments:
            return (f"unrecognized keyword '{cmd}'. Try one of "
                    f"`{'`, `'.join(possible_arguments)}`.")
        if cmd == "count" and "sample" not in kwargs.keys():
            return "count only usable with `sample` command"

    return None


@plugin.method("impscan")
def impscan(plugin, *args, **kwargs) -> Union[dict, list, str]:
    """Estimate breakdown of various lightning implementations on the network.
    This relies on the listnodes command and feature bits. Work in progress."""
    err = command_validation(args, kwargs)
    if err:
        return err
    # Run analysis on all network nodes
    if not kwargs and not args:
        return full_scan()
    for cmd, string in kwargs.items():
        if cmd == "node":
            return single_node_decode(string)
        if cmd == "features":
            return decode_features(string)
        if cmd == "test":
            return test_nodes(string)
        if cmd == "sample":
            if "count" in kwargs:
                return sample(string, kwargs["count"])
            return sample(string, None)
    for arg in args:
        return infer_usage(arg)


@plugin.init()
def init(options, configuration, plugin, **kwargs):
    plugin.log("Plugin impscan.py initialized")


plugin.run()
