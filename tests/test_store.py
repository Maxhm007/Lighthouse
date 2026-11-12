import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from lighthouse.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'events.db')
        self.store.init()

    def envelope(self):
        return {
            'proposal': {
                'sender': 'genesis', 'recipient': 'eve',
                'proposal_id': str(uuid4()), 'kind': 'hypothesis'
            },
            'auth': 'hmac-sha256', 'signature': 'placeholder',
        }

    def test_initial_status(self):
        self.assertEqual(self.store.status()['experiments'], 0)

    def test_envelope_never_implicitly_verified(self):
        result = self.store.record_envelope(self.envelope())
        self.assertEqual(result['verification_state'], 'unverified')
        self.assertEqual(self.store.status()['messages'][0]['count'], 1)

    def test_duplicate_uuid_normalization(self):
        envelope = self.envelope()
        self.store.record_envelope(envelope)
        envelope['proposal']['proposal_id'] = envelope['proposal']['proposal_id'].replace('-', '').upper()
        with self.assertRaises(Exception):
            self.store.record_envelope(envelope)

    def test_experiment_append(self):
        self.store.record_experiment('Pilot 1', 'joint', {'metric': 'tests passed', 'value': 2})
        self.assertEqual(self.store.status()['experiments'], 1)

    def test_invalid_peer_rejected(self):
        envelope = self.envelope()
        envelope['proposal']['sender'] = 'unknown'
        with self.assertRaises(ValueError):
            self.store.record_envelope(envelope)


if __name__ == '__main__':
    unittest.main()
