import unittest


class TestSample(unittest.TestCase):

    def test_sample(self):
        self.assertGreater(42, 1)


if __name__ == "__main__":
    unittest.main()
