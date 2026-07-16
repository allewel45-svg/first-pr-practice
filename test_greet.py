import unittest

from greet import greet


class GreetTests(unittest.TestCase):
    def test_greet_with_name(self):
        self.assertEqual(greet("Ada"), "Hello, Ada! Welcome aboard.")

    def test_greet_with_default_world(self):
        self.assertEqual(greet("World"), "Hello, World! Welcome aboard.")


if __name__ == "__main__":
    unittest.main()
