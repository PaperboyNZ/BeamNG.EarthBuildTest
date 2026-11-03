"""One job may share successful lot evidence, never blockers or failed reads."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import parking
from test_parking_surfaces import lots
from test_roads import FRAME, features, rules


class PreparedLotContextTests(unittest.TestCase):
    @staticmethod
    def md(material=''):
        road=features([[(0,50),(80,50)]],['service'],widths=[(0,6.)])
        road.rules['subclass']=rules([(0,'parking_aisle')])
        return SimpleNamespace(cell=lambda *a,**kw:SimpleNamespace(
            layers={'infrastructure':lots(material),'roads':road}))

    @staticmethod
    def elevation(a,b):return np.asarray(a)*0+10.

    def consumers(self,md,context=None,items=None):
        args=(FRAME,0,0,md,self.elevation)
        existing=[[10.,10.,10.,0.],[10.,10.,10.,0.,1],[20.,50.,10.,0.,1]]
        marks=[dict(m='line_white',w=.1,n=[[1.,1.,0.],[4.,1.,0.]])]
        return (parking.tile_lot_spots(*args,items,copy.deepcopy(existing),lot_context=context),
                parking.finish_markings(*args,items,copy.deepcopy(marks),lot_context=context))

    def test_lazy_success_prepares_once_and_matches_complete_standalone_outputs(self):
        for material in ('','asphalt','gravel','grass'):
            with self.subTest(material=material),patch('roads.cells_of_tile',return_value=['one-cell']):
                md=self.md(material)
                items=[(SimpleNamespace(ring=np.array(((10,25),(20,25),(20,35),(10,35)))),)]
                with patch.object(parking,'_lot_context',wraps=parking._lot_context) as prepare:
                    context=parking.prepare_lot_context(FRAME,0,0,md)
                    prepare.assert_not_called()
                    actual=self.consumers(md,context,items)
                    self.assertEqual(prepare.call_count,1)
                    expected=self.consumers(md,items=items)
                    self.assertEqual(prepare.call_count,3,'standalone consumers preserve their independent reads')
                self.assertEqual(actual,expected)
                self.assertTrue(actual[0])

    def test_transient_exception_uses_first_fallback_and_second_consumer_retries(self):
        md=self.md()
        with patch('roads.cells_of_tile',return_value=['one-cell']):
            value=parking._lot_context(FRAME,0,0,md)
            expected=parking.finish_markings(FRAME,0,0,md,self.elevation)
        with patch.object(parking,'_lot_context',side_effect=[ValueError('transient'),value]) as prepare:
            context=parking.prepare_lot_context(FRAME,0,0,md)
            existing=[[1.,1.,10.,0.]]
            self.assertEqual(parking.tile_lot_spots(FRAME,0,0,md,self.elevation,
                                                  existing=existing,lot_context=context),existing)
            actual=parking.finish_markings(FRAME,0,0,md,self.elevation,lot_context=context)
            self.assertEqual(actual,expected)
            self.assertEqual(prepare.call_count,2)
            self.assertIs(context(),value)
            self.assertEqual(prepare.call_count,2)

    def test_fault_during_preparation_is_not_cached_even_when_it_returns(self):
        md=self.md()
        with patch('roads.cells_of_tile',return_value=['one-cell']):
            value=parking._lot_context(FRAME,0,0,md)
            expected=self.consumers(md)
        faults=[7];calls=[]
        def prepare(*args):
            calls.append(args)
            if len(calls)==1:faults[0]+=1
            return value
        with patch('revisit.faults',side_effect=lambda:faults[0]),patch.object(parking,'_lot_context',side_effect=prepare):
            context=parking.prepare_lot_context(FRAME,0,0,md)
            self.assertEqual(self.consumers(md,context),expected)
            self.assertEqual(len(calls),2)
            self.assertIs(context(),value)
            self.assertEqual(len(calls),2)

    def test_items_are_read_again_when_marking_consumer_runs(self):
        md=self.md()
        spec=SimpleNamespace(ring=np.array(((200,200),(210,200),(210,210),(200,210))))
        items=[(spec,)]
        with patch('roads.cells_of_tile',return_value=['one-cell']), \
             patch.object(parking,'_lot_context',wraps=parking._lot_context) as prepare, \
             patch.object(parking,'_item_blockers',wraps=parking._item_blockers) as blockers:
            context=parking.prepare_lot_context(FRAME,0,0,md)
            self.assertTrue(parking.tile_lot_spots(FRAME,0,0,md,self.elevation,items,lot_context=context))
            spec.ring=np.array(((-10,20),(90,20),(90,80),(-10,80)))
            actual=parking.finish_markings(FRAME,0,0,md,self.elevation,items,lot_context=context)
            self.assertEqual(actual,[])
            self.assertEqual(prepare.call_count,1)
            self.assertEqual(blockers.call_count,2)
            self.assertEqual(actual,parking.finish_markings(FRAME,0,0,md,self.elevation,items))

    def test_prepared_instances_never_share_across_tile_frame_or_source(self):
        other_frame=SimpleNamespace(name='different frame')
        source=self.md();other_source=self.md()
        arguments=((FRAME,0,0,source),(FRAME,1,0,source),(other_frame,0,0,source),
                   (FRAME,0,0,other_source),(FRAME,0,0,source))
        values=[([],[]) for _ in arguments]
        with patch.object(parking,'_lot_context',side_effect=values) as prepare:
            contexts=[parking.prepare_lot_context(*args) for args in arguments]
            prepare.assert_not_called()
            for context,value in zip(contexts,values):
                self.assertIs(context(),value)
                self.assertIs(context(),value)
            self.assertEqual(prepare.call_count,len(arguments))
            self.assertEqual([call.args for call in prepare.call_args_list],list(arguments))

    def test_markings_only_job_prepares_on_its_first_consumer(self):
        md=self.md()
        with patch('roads.cells_of_tile',return_value=['one-cell']), \
             patch.object(parking,'_lot_context',wraps=parking._lot_context) as prepare:
            context=parking.prepare_lot_context(FRAME,0,0,md)
            prepare.assert_not_called()
            actual=parking.finish_markings(FRAME,0,0,md,self.elevation,lot_context=context)
            self.assertEqual(prepare.call_count,1)
            self.assertEqual(actual,parking.finish_markings(FRAME,0,0,md,self.elevation))


if __name__=='__main__':unittest.main()
