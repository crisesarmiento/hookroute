import json
import unittest
from dataclasses import FrozenInstanceError, replace
from unittest.mock import Mock

from hookroute import Decision, InputError, State, decide, parse_event, parse_routes


EVENT = {
    "repo": "demo",
    "workspace": "demo-feature",
    "workspace_path": "/work/demo/feature",
    "branch": "feature/demo",
    "git_remote": "git@example.invalid:team/demo.git",
    "state": "done",
    "timestamp": "2026-07-03T12:00:00Z",
}


def route(name="primary", selector='repo = "demo"', *, states='["done"]',
          url="https://example.invalid/hook"):
    return f'[[routes]]\nname = "{name}"\nstates = {states}\nurl = "{url}"\n{selector}\n'


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.event = parse_event(json.dumps(EVENT))

    def test_selectors_and_folder_boundaries(self):
        cases = [
            ('repo = "demo"', True),
            ('repo = "Demo"', False),
            ('workspace = "demo-feature"', True),
            ('workspace = "feature"', False),
            ('git_remote = "git@example.invalid:team/demo.git"', True),
            ('git_remote = "https://example.invalid/team/demo.git"', False),
            ('folder = "/work/demo/feature"', True),
            ('folder = "/work/demo/./"', True),
            ('folder = "/work/dem"', False),
            ('folder = "/work/demo/feat"', False),
            ('folder = "/work/demo/feature/child"', False),
            ('repo = "demo"\nworkspace = "demo-feature"\nfolder = "/work/demo"', True),
            ('repo = "demo"\nworkspace = "other"\nfolder = "/work/demo"', False),
        ]
        for selector, expected in cases:
            with self.subTest(selector=selector):
                result = decide(self.event, parse_routes(route(selector=selector)))
                self.assertEqual(result, Decision("primary", True, "rule_matched") if expected
                                 else Decision(None, False, "no_rule_matched"))
        missing_remote = replace(self.event, git_remote=None)
        self.assertFalse(decide(missing_remote, parse_routes(
            route(selector='git_remote = "git@example.invalid:team/demo.git"')
        )).would_send)

    def test_all_four_states(self):
        for state in State:
            with self.subTest(state=state):
                routes = parse_routes(route(states=f'["{state}"]'))
                self.assertTrue(decide(replace(self.event, state=state), routes).would_send)
                other = State.WAITING if state != State.WAITING else State.DONE
                self.assertFalse(decide(replace(self.event, state=other), routes).would_send)

    def test_first_fully_matching_rule(self):
        routes = parse_routes(
            route("off-state", states='["working"]')
            + route("off-pr", 'repo = "demo"\npr_open = true')
            + route("winner") + route("also-match")
        )
        self.assertEqual(decide(self.event, routes).rule, "winner")
        self.assertEqual(decide(self.event, parse_routes("routes = []")).rule, None)

    def test_pr_resolver_true_false_unknown(self):
        for expected in (True, False):
            rules = parse_routes(route(selector=f'repo = "demo"\npr_open = {str(expected).lower()}'))
            for actual in (True, False, None):
                with self.subTest(expected=expected, actual=actual):
                    stub = Mock(return_value=actual)
                    result = decide(self.event, rules, pr_open_resolver=stub)
                    self.assertEqual(result.would_send, actual is expected)
                    if actual is None:
                        self.assertEqual(result.reason, "pr_open_unknown")
                    stub.assert_called_once_with(self.event)
            self.assertEqual(decide(self.event, rules).reason, "pr_open_unknown")

    def test_pr_value_precedence_and_lazy_single_lookup(self):
        event = replace(self.event, pr_open=False)
        open_rule = route("open-pr", 'repo = "demo"\npr_open = true')
        closed_rule = route("closed-pr", 'repo = "demo"\npr_open = false')
        routes = parse_routes(open_rule + closed_rule)
        stub = Mock(return_value=False)
        self.assertEqual(decide(event, routes, pr_open_resolver=stub).rule, "closed-pr")
        stub.assert_not_called()
        self.assertEqual(decide(self.event, routes, pr_open_resolver=stub).rule, "closed-pr")
        stub.assert_called_once_with(self.event)
        unknown = Mock(return_value=None)
        self.assertEqual(decide(self.event, routes, pr_open_resolver=unknown).reason, "pr_open_unknown")
        unknown.assert_called_once_with(self.event)
        stub.reset_mock()
        no_candidate = replace(self.event, repo="not-demo")
        self.assertEqual(decide(no_candidate, routes, pr_open_resolver=stub).reason, "no_rule_matched")
        stub.assert_not_called()

    def test_immutable_validated_event(self):
        with self.assertRaises(FrozenInstanceError):
            self.event.repo = "other"
        with self.assertRaises(InputError):
            replace(self.event, state="not-a-state")
        event = parse_event(json.dumps(EVENT | {"head_sha": "a" * 40}))
        self.assertEqual(event.head_sha, "a" * 40)


class ParsingTests(unittest.TestCase):
    def test_invalid_event(self):
        cases = [
            "{broken", "null", "[]",
            json.dumps({key: value for key, value in EVENT.items() if key != "workspace"}),
            json.dumps(EVENT | {"extra": "untrusted"}),
            json.dumps(EVENT)[:-1] + ', "repo": "demo"}',
            json.dumps(EVENT | {"pr_open": float("nan")}),
        ]
        for key, value in [
            ("repo", ""), ("branch", ["branch"]), ("git_remote", " "),
            ("state", "untrusted"), ("state", {"untrusted": "value"}),
            ("workspace_path", "relative"), ("workspace_path", "/work/../repo"),
            ("timestamp", "2026-07-03T12:00:00"), ("timestamp", "2026-07-33T12:00:00Z"),
            ("timestamp", "2026-07-03T12:00:00+01:99"), ("head_sha", "untrusted"),
            ("pr_open", 1),
        ]:
            cases.append(json.dumps(EVENT | {key: value}))
        for source in cases:
            with self.subTest(source=source), self.assertRaises(InputError):
                parse_event(source)

    def test_invalid_routes(self):
        cases = [
            "", "routes = {}", "routes = [1]", "routes = []\nother = 1",
            '[[routes]]\nname = "unclosed', route() + route(), route(name="bad name"),
            route(selector=""), route(selector='repo = "demo"\nextra = "untrusted"'),
            route(selector='repo = 123'), route(selector='folder = "/work/../demo"'),
            route(selector='repo = "demo"\npr_open = 0'),
            route(states='"done"'), route(states="[]"), route(states='["done", "done"]'),
            route(states='["untrusted"]'), route(states="[1]"),
            route().replace('url = "https://example.invalid/hook"\n', ""),
        ]
        for url in [
            "ftp://example.invalid/hook", "https:///hook", "https://./hook",
            "https://user@example.invalid/hook", "https://user:pwd@example.invalid/hook",
            "https://example.invalid/hook?token=value", "https://example.invalid/hook?",
            "https://example.invalid/hook#value", "https://example.invalid/hook#",
            "https://example.invalid:99999/hook", "https://example.invalid:bad/hook",
            "https://example.invalid/%xx", "https://[not-ip]/hook",
            "https://example.invalid/bad path",
        ]:
            cases.append(route(url=url))
        for source in cases:
            with self.subTest(source=source), self.assertRaises(InputError):
                parse_routes(source)

    def test_http_with_port_and_ipv6(self):
        for url in ("http://localhost:8080/hook", "https://[::1]:443/hook"):
            with self.subTest(url=url):
                self.assertEqual(parse_routes(route(url=url))[0].url, url)
