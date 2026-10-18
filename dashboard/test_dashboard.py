"""Dashboard tests: file presence, the JSON fields the UI reads, fixture
determinism, and a real HTTP smoke test of the static server.

Run from the repository root:  python -m pytest -q
"""

import functools
import http.server
import importlib.util
import json
import os
import threading
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEMO = os.path.join(ROOT, 'demo')

RESULT_DISPATCH_KEYS = {'batch_id', 'destination_id', 'quantity_kg', 'discount_pct',
                        'effective_price_per_kg', 'sold_kg', 'expected_contribution', 'reason'}
RESULT_METRIC_KEYS = {'net_revenue', 'spoiled_kg', 'fulfillment_pct',
                      'harvested_kg', 'dispatched_kg', 'demand_kg', 'feasible'}


def _load_serve():
    spec = importlib.util.spec_from_file_location('aurenza_dashboard_serve',
                                                  os.path.join(HERE, 'serve.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestDashboardFiles(unittest.TestCase):
    def test_required_files_exist(self):
        for name in ('index.html', 'app.js', 'styles.css', 'serve.py'):
            self.assertTrue(os.path.isfile(os.path.join(HERE, name)), f'missing {name}')

    def test_app_reads_only_demo_json(self):
        src = open(os.path.join(HERE, 'app.js'), encoding='utf-8').read()
        self.assertIn('../demo/result.json', src)
        self.assertIn('../demo/evaluation.json', src)
        # the dashboard must not import engine code (contract §10)
        self.assertNotIn('import ', src.split('\n')[0])


class TestConsumedSchema(unittest.TestCase):
    def test_result_json_has_fields_dashboard_reads(self):
        with open(os.path.join(DEMO, 'result.json'), encoding='utf-8') as fh:
            r = json.load(fh)
        self.assertIn('results', r)
        self.assertIn('improvement', r)
        for strategy in ('baseline', 'planner'):
            block = r['results'][strategy]
            self.assertTrue(RESULT_METRIC_KEYS.issubset(block['metrics'].keys()))
            self.assertTrue(block['dispatches'], f'{strategy} has no dispatches')
            for d in block['dispatches']:
                self.assertTrue(RESULT_DISPATCH_KEYS.issubset(d.keys()))
            self.assertTrue(block['reconciliation']['check_ok'])
        for key in ('net_revenue', 'spoilage_kg', 'fulfillment_pct'):
            self.assertIn(key, r['improvement'])

    def test_evaluation_json_shape(self):
        with open(os.path.join(DEMO, 'evaluation.json'), encoding='utf-8') as fh:
            e = json.load(fh)
        self.assertEqual(e['mode'], 'standard')
        self.assertTrue(e['scenarios'])
        for sc in e['scenarios']:
            for k in ('scenario_id', 'disruption', 'runs', 'summary'):
                self.assertIn(k, sc)
            run = sc['runs'][0]
            for k in ('seed', 'baseline', 'planner', 'improvement', 'win'):
                self.assertIn(k, run)
            self.assertIn('metrics', run['baseline'])
            self.assertIn('metrics', run['planner'])

    def test_committed_evaluation_matches_engine(self):
        """The committed fixture must equal a fresh run (reproducible + deterministic)."""
        from engine.scripts import run_eval
        with open(os.path.join(DEMO, 'evaluation.json'), encoding='utf-8') as fh:
            committed = json.load(fh)
        self.assertEqual(committed, run_eval.evaluate('standard'))


class TestDashboardMarkup(unittest.TestCase):
    """Every element id app.js writes into must exist in index.html, and the
    page must load its own assets (no build step, no CDN)."""

    HTML_IDS = ('loading', 'load-error', 'footer', 'detail-meta', 'detail-verdict',
                'detail-notes', 'hero', 'kpi-cards', 'planner-summary', 'planner-dispatches',
                'baseline-summary', 'baseline-dispatches', 'batch-table', 'recon',
                'eval-meta', 'eval-notes', 'eval-cards', 'eval-charts',
                'scenario-select', 'scenario-view', 'tab-overview', 'tab-evaluation',
                'view-overview', 'view-evaluation')

    @classmethod
    def setUpClass(cls):
        cls.html = open(os.path.join(HERE, 'index.html'), encoding='utf-8').read()

    def test_render_targets_present(self):
        for el_id in self.HTML_IDS:
            self.assertIn(f'id="{el_id}"', self.html, f'index.html missing id="{el_id}"')

    def test_local_assets_linked(self):
        self.assertIn('href="styles.css"', self.html)
        self.assertIn('src="app.js"', self.html)
        self.assertNotIn('http://', self.html.replace('http://www.w3.org', ''))
        self.assertNotIn('https://', self.html.replace('https://www.w3.org', ''))


class TestStaticServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        serve = _load_serve()
        handler = functools.partial(serve.Handler, directory=serve.ROOT)
        cls.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path):
        url = f'http://127.0.0.1:{self.port}{path}'
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, resp.read()

    def test_dashboard_assets_served(self):
        for path in ('/dashboard/index.html', '/dashboard/app.js',
                     '/dashboard/styles.css', '/dashboard/'):
            status, body = self._get(path)
            self.assertEqual(status, 200, path)
            self.assertTrue(body, path)

    def test_engine_json_served_and_parses(self):
        for path in ('/demo/result.json', '/demo/evaluation.json'):
            status, body = self._get(path)
            self.assertEqual(status, 200, path)
            json.loads(body.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
