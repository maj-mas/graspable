import unittest
import subprocess
import graspable


class TestInitialisation(unittest.TestCase):

    def test_empty_config(self):
        with self.assertRaises(RuntimeError) as exc:
            graspable_instance = graspable.GraspableMain()
            graspable_instance.main(cfg="tests/empty_cfg.yaml")


if __name__ == "__main__":
    unittest.main()
