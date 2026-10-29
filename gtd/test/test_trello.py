

import unittest
from unittest.mock import patch, MagicMock, call
import datetime as _dt


import gtd.trello as mod 


# ---------------------------------------------------------------------------
#  Pure utility helpers
# ---------------------------------------------------------------------------

class TestUtilityFunctions(unittest.TestCase):

    def test_utc_to_this_tz_valid_roundtrip(self):
        """Conversion returns a `datetime` close to local `now()`."""
        utc_now = _dt.datetime.utcnow()
        utc_str = utc_now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        local_dt = mod.utc_to_this_tz(utc_str)
        self.assertIsInstance(local_dt, _dt.datetime)

        # Result should be within two seconds of the real local time.
        self.assertLess(
            abs((local_dt - _dt.datetime.now()).total_seconds()),
            2.0
        )

    def test_utc_to_this_tz_invalid_string(self):
        self.assertIsNone(mod.utc_to_this_tz("definitely‑not‑a‑date"))

    def test_CheckField(self):
        has_due = mod.CheckField("due")
        self.assertTrue(has_due({"due": "2025‑05‑09"}))
        self.assertFalse(has_due({"something": 1}))
        self.assertFalse(has_due({"due": None}))

    def test_NotCheckField(self):
        not_due = mod.NotCheckField("due")
        self.assertTrue(not_due({"x": 1}))
        self.assertFalse(not_due({"due": "foo"}))


# ---------------------------------------------------------------------------
#  Tests that exercise TrelloAPI methods with heavy mocking
# ---------------------------------------------------------------------------

class TestTrelloAPI(unittest.TestCase):

    def setUp(self):
        # Patch out configuration reads so that constructor succeeds.
        cfg_patch = patch(
            f"{mod.__name__}.get_config_str",
            side_effect=lambda key, default='', desc=None: {
                "trello_apikey": "dummy‑key",
                "trello_token": "dummy‑token",
                "trello_board": "Work",
            }.get(key, default)
        )
        self.mock_cfg = cfg_patch.start()
        self.addCleanup(cfg_patch.stop)

        # Patch the trello.TrelloApi SDK class.
        trello_patch = patch(f"{mod.__name__}.trello.TrelloApi")
        self.MockTrelloApiClass = trello_patch.start()
        self.addCleanup(trello_patch.stop)

        #  Build a fully‑featured mock TrelloApi instance:
        self.mock_api = MagicMock()
        # nested service proxies that the production code expects
        self.mock_api.cards = MagicMock()
        self.mock_api.boards = MagicMock()
        self.mock_api.lists = MagicMock()
        self.mock_api.checklists = MagicMock()
        self.MockTrelloApiClass.return_value = self.mock_api

        # Construct the client under test.
        self.client = mod.TrelloAPI()

    # ---------------  get_board / get_default_board ---------------

    def test_get_board_success(self):
        boards = [{'name': 'Work', 'id': 'b123'}]
        with patch.object(self.client, 'get_boards', return_value=boards):
            board = self.client.get_board('Work')
        self.assertEqual(board['id'], 'b123')

    def test_get_board_not_found(self):
        with patch.object(self.client, 'get_boards', return_value=[]):
            with self.assertRaises(ValueError):
                self.client.get_board('NoSuchBoard')

    def test_get_default_board_falls_back_to_config(self):
        boards = [{'name': 'Whatever', 'id': '42'}]
        with patch.object(self.client, 'get_boards', return_value=boards):
            self.assertEqual(self.client.get_default_boards(), ["Work"])  # from config

    # -----------------------  has_label  --------------------------

    def test_has_label(self):
        card = {'labels': [{'name': 'Bug'}, {'name': 'Idea'}]}
        self.assertTrue(self.client.has_label(card, 'Bug'))
        self.assertFalse(self.client.has_label(card, 'Urgent'))

    # ----------------------  remove_label  ------------------------

    def test_remove_label_success(self):
        card = {
            'id': 'c1',
            'labels': [{'id': 'lab_99', 'name': 'Done'}]
        }
        self.mock_api.cards.delete_idLabel_idLabel = MagicMock()

        self.client.remove_label(card, 'Done')

        self.mock_api.cards.delete_idLabel_idLabel.assert_called_once_with(
            'lab_99', 'c1'
        )

    def test_remove_label_raises_when_missing(self):
        card = {'id': 'c1', 'labels': []}
        with self.assertRaises(ValueError):
            self.client.remove_label(card, 'NonExisting')

    # --------------------  get_list_name --------------------------

    def test_get_list_name(self):
        card = {'idList': 'list_abc'}
        self.mock_api.lists.get.return_value = {'name': 'Backlog'}

        name = self.client.get_list_name(card)

        self.mock_api.lists.get.assert_called_once_with('list_abc')
        self.assertEqual(name, 'Backlog')


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
