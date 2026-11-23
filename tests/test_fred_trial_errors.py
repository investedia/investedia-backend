"""FRED proxy error categories are useful without exposing provider messages."""
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import calendar_fred as fred

class FredTrialErrorTests(unittest.TestCase):
    def check_error(self, payload):
        error = HTTPError('https://api.stlouisfed.org/fred/releases/dates?api_key=must-not-leak', 400, 'Bad Request', {}, io.BytesIO(json.dumps(payload).encode()))
        with patch.object(fred.urllib.request, 'urlopen', side_effect=error):
            with self.assertRaises(fred.FredError) as caught:
                fred._get('releases/dates', {}, 'must-not-leak')
        self.assertNotIn('must-not-leak', str(caught.exception))
        self.assertNotIn('https:', str(caught.exception))
        return str(caught.exception)

    def test_known_reason_is_preserved(self):
        self.assertEqual(self.check_error({'trial_fred_reason': 'key_rejected', 'raw': 'must-not-leak'}), 'releases/dates: HTTP 400 [key_rejected]')

    def test_unknown_reason_and_raw_provider_message_are_not_exposed(self):
        self.assertEqual(self.check_error({'trial_fred_reason': 'must-not-leak', 'error_message': 'must-not-leak'}), 'releases/dates: HTTP 400')

if __name__ == '__main__':
    unittest.main()
