import random
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from PIL import Image

from core.models import ImageLayer, Project, Page
from core.image_geometry import get_image_layer_crop_box
from core.project import save_project_to_json, load_project_from_json
from ui.crop_dialog import CropDialog
from ui.crop_geometry import (ASPECT_MODES, get_aspect_ratio, fit_crop_to_ratio,
                              resize_crop_with_ratio, snap_crop_to_pixels, minimum_crop_size)


class CropAspectRatioTests(unittest.TestCase):
    def assert_valid(self, box, size, ratio):
        l,t,r,b=box
        self.assertGreaterEqual(l, -1e-8)
        self.assertGreaterEqual(t, -1e-8)
        self.assertLessEqual(r, size[0]+1e-8)
        self.assertLessEqual(b, size[1]+1e-8)
        min_w,min_h=minimum_crop_size(size)
        self.assertGreaterEqual(r-l+1e-8,min_w)
        self.assertGreaterEqual(b-t+1e-8,min_h)
        self.assertAlmostEqual((r-l)/(b-t),ratio,places=8)
        pixel_box=snap_crop_to_pixels(box,size)
        self.assertGreaterEqual(pixel_box[2]-pixel_box[0],min_w)
        self.assertGreaterEqual(pixel_box[3]-pixel_box[1],min_h)

    def test_original_uses_actual_source_size(self):
        self.assertEqual(get_aspect_ratio('Original',(1200,800)),1.5)
        self.assertEqual(get_aspect_ratio('Original',(800,1200)),2/3)
        self.assertIsNone(get_aspect_ratio('Free',(1200,800)))

    def test_presets_fit_selection_and_preserve_center(self):
        box=[100,100,900,700]
        for mode,expected in [('Original',(800,600)),('1:1',(600,600)),
                              ('9:16',(337.5,600)),('16:9',(800,450))]:
            with self.subTest(mode=mode):
                ratio=get_aspect_ratio(mode,(1200,900))
                result=fit_crop_to_ratio(box,(1200,900),ratio)
                l,t,r,b=result
                self.assert_valid(result,(1200,900),ratio)
                self.assertEqual(((l+r)/2,(t+b)/2),(500,400))
                self.assertEqual((r-l,b-t),expected)
                self.assertTrue(l>=box[0] and t>=box[1] and r<=box[2] and b<=box[3])

    def test_minimum_expansion_shifts_only_when_needed(self):
        size=(1000,1000)
        ratio=16/9
        box=fit_crop_to_ratio([990,990,1000,1000],size,ratio)
        self.assert_valid(box,size,ratio)
        self.assertEqual(box[2],1000)
        self.assertEqual((box[1]+box[3])/2,995)
        self.assertEqual(box[3]-box[1],10)

    def test_corner_resize_keeps_opposite_anchor(self):
        size=(1200,900)
        for mode in ASPECT_MODES[1:]:
            ratio=get_aspect_ratio(mode,size)
            box=fit_crop_to_ratio([200,100,1000,800],size,ratio)
            for handle in ['nw','ne','sw','se']:
                for dx,dy in [(-5000,-5000),(5000,5000),(-5000,5000),(5000,-5000),(30,20),(0,0)]:
                    with self.subTest(mode=mode,handle=handle,delta=(dx,dy)):
                        result=resize_crop_with_ratio(box,size,handle,dx,dy,ratio)
                        self.assert_valid(result,size,ratio)
                        ax=2 if 'w' in handle else 0
                        ay=3 if 'n' in handle else 1
                        self.assertAlmostEqual(result[ax],box[ax])
                        self.assertAlmostEqual(result[ay],box[ay])
                        if dx==dy==0:
                            for actual,expected in zip(result,box):self.assertAlmostEqual(actual,expected)

    def test_edge_resize_keeps_ratio_bounds_and_opposite_edge(self):
        size=(1200,900)
        for mode in ASPECT_MODES[1:]:
            ratio=get_aspect_ratio(mode,size)
            box=fit_crop_to_ratio([120,90,1080,810],size,ratio)
            for handle,anchor in [('w',2),('e',0),('n',3),('s',1)]:
                for delta in [-10000,0,10000]:
                    result=resize_crop_with_ratio(box,size,handle,delta,delta,ratio)
                    self.assert_valid(result,size,ratio)
                    self.assertAlmostEqual(result[anchor],box[anchor])

    def test_varied_source_sizes_and_near_border_selections(self):
        rng=random.Random(19)
        for size in [(17,19),(401,799),(1920,1080),(1080,1920),(1,1)]:
            for mode in ASPECT_MODES[1:]:
                ratio=get_aspect_ratio(mode,size)
                for _ in range(20):
                    l,t=rng.uniform(0,size[0]),rng.uniform(0,size[1])
                    r,b=rng.uniform(l,size[0]),rng.uniform(t,size[1])
                    try:
                        box=fit_crop_to_ratio([l,t,r,b],size,ratio)
                    except ValueError:
                        min_w,min_h=minimum_crop_size(size)
                        self.assertGreater(max(min_h,min_w/ratio),min(size[1],size[0]/ratio))
                        continue
                    self.assert_valid(box,size,ratio)
                    result=resize_crop_with_ratio(box,size,'se',-500,1000,ratio)
                    self.assert_valid(result,size,ratio)

    def test_impossible_ratio_preserves_minimum_by_rejecting(self):
        with self.assertRaises(ValueError):fit_crop_to_ratio([0,0,1,1000],(1,1000),1)

    def test_free_motion_unchanged(self):
        box=[20,10,120,80]
        self.assertEqual(fit_crop_to_ratio(box,(200,100),None),box)
        fake=SimpleNamespace(source=Image.new('RGBA',(200,100)),sx=1,sy=1,
                             _aspect_ratio=None,_draw=Mock(),_drag=('se',0,0,box))
        CropDialog._motion(fake,SimpleNamespace(x=20,y=5))
        self.assertEqual(fake.box,[20,10,140,85])

    def test_switch_to_free_snaps_fractional_box_without_losing_minimum(self):
        fake=SimpleNamespace(source=Image.new('RGBA',(10,10)),box=[1.5,1.5,2.5,2.5],
                             aspect_var=Mock(),_draw=Mock())
        fake.aspect_var.get.return_value='Free'
        CropDialog._aspect_changed(fake)
        self.assertIsNone(fake._aspect_ratio)
        self.assertEqual(fake.box,[2,2,3,3])

    def test_locked_move_and_reset(self):
        box=fit_crop_to_ratio([20,10,180,90],(200,100),16/9)
        fake=SimpleNamespace(source=Image.new('RGBA',(200,100)),sx=1,sy=1,
                             _aspect_ratio=16/9,_draw=Mock(),_drag=('move',0,0,box),aspect_var=Mock())
        CropDialog._motion(fake,SimpleNamespace(x=1000,y=-1000))
        self.assert_valid(fake.box,(200,100),16/9)
        self.assertAlmostEqual(fake.box[2],200)
        self.assertAlmostEqual(fake.box[1],0)
        CropDialog.reset(fake)
        self.assertEqual(fake.box,[0,0,200,100])
        self.assertIsNone(fake._aspect_ratio)
        fake.aspect_var.set.assert_called_with('Free')

    def test_apply_pixel_snapping_and_unchanged_schema_roundtrip(self):
        size=(403,799)
        layer=ImageLayer(original_width=1,original_height=1)
        original_keys=set(layer.to_dict())
        box=fit_crop_to_ratio([22,40,380,770],size,9/16)
        fake=SimpleNamespace(source=Image.new('RGBA',size),layer=layer,box=box,
                             destroy=Mock(),on_apply=Mock())
        CropDialog.apply(fake)
        self.assertEqual(get_image_layer_crop_box(layer,size),tuple(snap_crop_to_pixels(box,size)))
        self.assertEqual(set(layer.to_dict()),original_keys)
        with tempfile.TemporaryDirectory() as tmp:
            path=str(Path(tmp)/'crop.json')
            project=Project(pages=[Page(layers=[layer])])
            self.assertTrue(save_project_to_json(project,path)[0])
            loaded,message=load_project_from_json(path)
            self.assertIsNotNone(loaded,message)
            self.assertEqual(loaded.to_dict(),project.to_dict())


if __name__=='__main__':unittest.main()
