import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from biox_v13_core import PFM_ORDER, load_materials, order_from


class V13CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.materials = load_materials(
            Path(__file__).resolve().parents[1] / "config" / "materials_2d.json"
        )

    def test_reported_2d_coefficients_and_order(self):
        values = {name: material.d11_derived_pm_per_v for name, material in self.materials.items()}
        self.assertEqual(order_from(values), list(PFM_ORDER))

    def test_pfm_targets_are_apparent_and_ordered(self):
        values = {name: material.pfm_target.d33_app_pm_per_v for name, material in self.materials.items()}
        self.assertEqual(order_from(values), list(PFM_ORDER))

    def test_effective_conversion_has_expected_units_and_shape(self):
        c3d, e3d, eps = self.materials["BiOI"].effective_3d(1.0)
        self.assertEqual((len(c3d), len(c3d[0])), (6, 6))
        self.assertEqual((len(e3d), len(e3d[0])), (3, 6))
        self.assertGreater(c3d[0][0], 1e9)
        self.assertGreater(e3d[2][0], 0.0)
        self.assertGreater(eps[2][2], 0.0)

    def test_dft_apparent_inputs_are_positive_and_ordered(self):
        materials = load_materials(
            Path(__file__).resolve().parents[1] / "config" / "materials_dft_apparent.json"
        )
        values = {name: material.pfm_target.d33_app_pm_per_v for name, material in materials.items()}
        self.assertEqual(order_from(values), list(PFM_ORDER))
        for material in materials.values():
            c3d, e3d, eps = material.dft_apparent_3d()
            self.assertEqual((len(c3d), len(c3d[0])), (6, 6))
            self.assertEqual((len(e3d), len(e3d[0])), (3, 6))
            self.assertGreater(c3d[2][2], 0.0)
            self.assertGreater(e3d[2][2], 0.0)
            self.assertGreater(eps[2][2], 0.0)


if __name__ == "__main__":
    unittest.main()
