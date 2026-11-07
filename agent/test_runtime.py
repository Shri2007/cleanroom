"""Agent-local checks. No model calls or changes outside agent/."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.builder import build
from agent.compat import calendar,check_cal
from agent.coordinator import Coordinator,format_report,parse_command
from agent.verifier import verify


class RealAdapterTests(unittest.TestCase):
    def test_real_brain_is_required(self):
        with patch('agent.builder.function',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'stub mode is disabled'):
                build({'train_lines':[]},lambda event:None)

    def test_real_brain_selection_and_code_are_preserved(self):
        observed=[]
        def real(lines,on_event):
            observed.extend(lines)
            on_event({'step':'score','version':1,'train_pct':50,'held_pct':None,'kept':True})
            return dict(best_version=1,train_pct=50,held_pct=None,rules=[],code='globalThis.Cal={run(){return ""}}')
        with patch('agent.builder.function',return_value=real):
            result=build({'train_lines':[{'test':7}]},lambda event:None)
        self.assertEqual(observed,[{'test':7}])
        self.assertFalse(result['stub'])
        self.assertEqual(result['brain_backend'],'server.brain.run_cal')

    def test_current_calendar_and_checker_interfaces(self):
        rows=calendar([(9,1752),(9,1751),(2,1700)])
        self.assertEqual([row['test'] for row in rows],[1,2,3])
        self.assertTrue(all(row['source']=='text' and isinstance(row['output'],str) for row in rows))
        table={f"{row['args'][0]}:{row['args'][1]}":row['output'] for row in rows}
        code='globalThis.Cal={run(m,y){const d='+json.dumps(table)+';return d[m+":"+y]||""}}'
        result=check_cal(code,rows,[2,3])
        self.assertEqual((result['matched'],result['total']),(2,2))
        self.assertTrue(all(row['pass'] for row in result['tests']))

    def test_verifier_refuses_training_overlap(self):
        with self.assertRaisesRegex(ValueError,'overlap'):
            verify({'code':'','train_tests':[1],'held_out_lines':[{'test':1}]})

    def test_report_uses_independent_result_and_dates(self):
        snapshot=dict(stub=False,scores=[dict(version=2,train_pct=100,kept=True)],rules=[dict(status='seen',rule='2 to 14')],
                      september_1752='September 1752',held_out_dates={'8':[9,1751]},
                      verification=dict(match_pct=0,matched=0,total=1,tests=[{'test':8,'pass':False}]))
        self.assertIn('FAIL',format_report(snapshot))
        self.assertIn('1751',format_report(snapshot,'tests'))
        self.assertIn('✓ seen',format_report(snapshot,'rules'))

    def test_mentions_stay_allowlisted(self):
        self.assertEqual(parse_command('@agent1ours rebuild cal','agent1ours')[0],('rebuild','cal'))
        self.assertEqual(parse_command('@agent1ours rebuild evil','agent1ours')[1],'Unknown target.')


if __name__=='__main__':unittest.main()
