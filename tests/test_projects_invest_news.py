import json, tempfile, unittest
from pathlib import Path
from unittest import mock

from tools.projects.invest import news_match


def story(i, h, s='', country='India', impacts=()):
    return {'id': i, 'headline': h, 'summary': s, 'location': {'country': country}, 'impacts': list(impacts), 'source': {'name': 'Fixture', 'url': 'https://example.test/' + i}}


class NewsMatch(unittest.TestCase):
    def run_on(self, stories):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'news-archive.json').write_text(json.dumps({'stories': stories}))
            out = Path(d, 'out.json')
            with mock.patch.object(news_match, 'ROOT', news_match.ROOT), mock.patch('sys.argv', ['x', d]), \
                 mock.patch.object(Path, 'write_text', lambda self, t, *a, **k: out.open('w').write(t) if self.name == 'project-news.json' else Path.write_text.__wrapped__(self, t) if hasattr(Path.write_text, '__wrapped__') else open(self, 'w').write(t)):
                news_match.main()
            return json.loads(out.read_text())['matches']

    def test_true_mentions_match_and_generic_words_do_not(self):
        m = self.run_on([
            story('a', 'SJVN diverts Satluj for Luhri Stage-I? No: Sunni Dam hydro project civil works progress', 'SJVN said the 382 MW Sunni Dam HEP received approval.'),
            story('b', "IEA Forecasts UAE to Become World's Largest Solar Generator per Capita", 'Middle East solar growth', 'United Arab Emirates'),
            story('c', 'Tesla to Wind Down Cybertruck Production', 'pioneer of EVs', 'United States'),
            story('d', 'NHPC: Dibang Multipurpose project dam concreting delayed by monsoon', 'NHPC hydro', 'India'),
        ])
        names = {(x['project_name'], x['article']) for x in m}
        self.assertNotIn('b', {a for _, a in names})
        self.assertNotIn('c', {a for _, a in names})
        self.assertIn(('Dibang Multipurpose hydroelectric plant', 'd'), names)
        d = next(x for x in m if x['article'] == 'd')
        self.assertEqual(d['status'], 'confirmed')
        self.assertIn('delay', d['events'])
        self.assertIsNone(d['sentiment'])


if __name__ == '__main__':
    unittest.main()
