import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from red_pill.memory import MemoryManager

class TestQdrantCompat(unittest.TestCase):
    def setUp(self):
        # Mock cfg to avoid real qdrant connection
        with patch('red_pill.config.QDRANT_MODE', 'server'):
            with patch('red_pill.config.QDRANT_URL', 'http://localhost:6333'):
                with patch('red_pill.config.QDRANT_API_KEY', 'test'):
                    self.mm = MemoryManager()
        
        # Mock encoder
        self.mm.encoder = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.tolist.return_value = [0.1] * 384
        self.mm.encoder.embed.return_value = [mock_embedding]

    def test_search_and_reinforce_fallback_to_search(self):
        # Mock client to throw AttributeError on query_points
        self.mm.client.query_points = MagicMock(side_effect=AttributeError("'QdrantClient' object has no attribute 'query_points'"))
        
        # Mock .search to return something
        mock_hit = MagicMock()
        mock_hit.id = "test-id"
        mock_hit.payload = {"content": "test", "reinforcement_score": 1, "associations": []}
        self.mm.client.search = MagicMock(return_value=[mock_hit])
        
        # Mock _ensure_collection and retrieve/set_payload
        self.mm._ensure_collection = MagicMock()
        self.mm.client.retrieve = MagicMock(return_value=[mock_hit])
        self.mm.client.set_payload = MagicMock()

        results = self.mm.search_and_reinforce("test_collection", "test query")
        
        self.mm.client.query_points.assert_called_once()
        self.mm.client.search.assert_called_once()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, "test-id")

    def test_search_and_reinforce_fallback_to_rest(self):
        # Mock client to throw AttributeError on query_points and search
        self.mm.client.query_points = MagicMock(side_effect=AttributeError("'QdrantClient' object has no attribute 'query_points'"))
        delattr(self.mm.client, 'search') if hasattr(self.mm.client, 'search') else None
        
        # Mock search_points on http.search_api
        mock_hit = MagicMock()
        mock_hit.id = "rest-id"
        mock_hit.payload = {"content": "rest", "reinforcement_score": 1, "associations": []}
        
        self.mm.client.http = MagicMock()
        self.mm.client.http.search_api = MagicMock()
        self.mm.client.http.search_api.search_points = MagicMock(return_value=[mock_hit])
        
        # Mock _ensure_collection and retrieve/set_payload
        self.mm._ensure_collection = MagicMock()
        self.mm.client.retrieve = MagicMock(return_value=[mock_hit])
        self.mm.client.set_payload = MagicMock()

        results = self.mm.search_and_reinforce("test_collection", "test query")
        
        self.mm.client.http.search_api.search_points.assert_called_once()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, "rest-id")

if __name__ == '__main__':
    unittest.main()
