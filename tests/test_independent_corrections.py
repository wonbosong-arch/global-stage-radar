"""Independent fixtures anchored to cited official documents, not generated status labels."""
import csv
import hashlib
import json
import math
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(path):
    with (ROOT/path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

EXPECTED={
 '512290':('930726','中证生物医药指数'),
 '512400':('000819','中证申万有色金属指数'),
 '512660':('399967','中证军工指数'),
 '512690':('399987','中证酒指数'),
 '515030':('399976','中证新能源汽车指数'),
 '515120':('931152','中证创新药产业指数'),
 '515210':('930606','中证钢铁指数'),
 '516970':('399995','中证基建工程指数'),
}

class Corrections(unittest.TestCase):
    def setUp(self):
        self.reg={r['symbol']:r for r in read('research/china_mainland_30_etf_verification_register.csv')}
        self.sel=read('research/china_sector_representative_12_selection.csv')
        self.methods={r['index_code']:r for r in read('research/china_index_official_methodology_evidence.csv')}

    def test_eight_official_index_fixtures(self):
        for symbol,(code,name) in EXPECTED.items():
            with self.subTest(symbol=symbol):
                self.assertEqual((self.reg[symbol]['tracked_index_code'],self.reg[symbol]['tracked_index_name_zh']),(code,name))
                self.assertEqual(self.methods[code]['index_name_zh'],name)
                self.assertIn(symbol,self.methods[code]['linked_etf_symbols'].split(';'))
                self.assertTrue(self.reg[symbol]['official_source_url'].startswith('https://'))

    def test_official_legal_names(self):
        expected={'512660':'国泰中证军工交易型开放式指数证券投资基金','515120':'广发中证创新药产业交易型开放式指数证券投资基金','512760':'国泰CES半导体芯片行业交易型开放式指数证券投资基金'}
        for symbol,name in expected.items():self.assertEqual(self.reg[symbol]['official_name_zh'],name)

    def test_selection_mapping_and_rationale_consistency(self):
        register=read('research/china_mainland_30_etf_verification_register.csv')
        self.assertEqual(len(register),30)
        self.assertEqual(len(self.reg),30)
        self.assertEqual(len(self.sel),12)
        self.assertEqual(len({r['symbol'] for r in self.sel}),12)
        self.assertEqual({r['symbol'] for r in self.sel},
                         {r['symbol'] for r in register if r['representative_selection_status']=='selected_representative'})
        self.assertEqual({r['symbol'] for r in read('research/china_mainland_30_etf_ohlcv_structure_audit.csv')},set(self.reg))
        evidence=read('research/official_identity_index_evidence.csv')
        self.assertEqual(len(evidence),30)
        self.assertEqual({r['symbol'] for r in evidence},set(self.reg))
        for r in evidence:
            self.assertEqual(self.reg[r['symbol']]['tracked_index_code'],r['audited_index_code'])
            self.assertEqual(self.reg[r['symbol']]['official_name_zh'],r['audited_name_zh'])
        self.assertEqual(len(self.methods),29)
        self.assertEqual(set(self.methods),{r['tracked_index_code'] for r in register})
        for r in self.sel:
            reg=self.reg[r['symbol']]
            self.assertEqual(r['tracked_index_code'],reg['tracked_index_code'])
            self.assertEqual(r['selection_rationale'],reg['selection_rationale'])
            self.assertEqual(r['sector_category'],reg['sector_category'])
            self.assertEqual(r['selection_approval'],'provisional_research_only')
            self.assertEqual(r['selection_does_not_assert_stage2'],'true')

    def test_overlap_types_are_distinct(self):
        a,b,c,d=[self.reg[s] for s in ['512700','512800','512480','512760']]
        self.assertEqual(a['tracked_index_code'],b['tracked_index_code'])
        self.assertNotEqual(c['tracked_index_code'],d['tracked_index_code'])
        self.assertEqual(a['representative_selection_status'],'hold_same_index_duplicate')
        self.assertEqual(d['representative_selection_status'],'hold_high_correlation_alternative')

    def test_unverified_gates_and_versions_stay_closed(self):
        for r in self.reg.values():
            for field in ['korean_broker_tradability','adjusted_price_quality','data_rights','latest_methodology_version_status']:
                self.assertEqual(r[field],'unverified_pending')
            self.assertEqual(r['activation_status'],'inactive_research_only')
        for r in read('research/china_etf_promotion_gates.csv'):
            self.assertEqual(r['activate'],'false')
            self.assertEqual(r['latest_methodology_version_verified'],'false')
            for key in ['broker_tradability_verified','adjusted_prices_verified','data_rights_verified']:self.assertEqual(r[key],'false')
            self.assertEqual(r['official_index_methodology_verified']=='true',r['symbol']=='512480')

    def test_methodology_level_matches_available_evidence(self):
        verified=[code for code,r in self.methods.items() if r['review_status']=='verified_rules_in_cited_version']
        self.assertEqual(verified,['H30184'])
        for r in self.methods.values():
            self.assertEqual(r['latest_version_verified'],'false')
            self.assertEqual(r['constituent_overlap_verified'],'false')
            self.assertNotIn('#/',r['methodology_evidence_url'])
            self.assertTrue(r['factsheet_evidence_url'].endswith(r['index_code']+'factsheet.pdf'))
        self.assertNotIn('15 percent cap',self.methods['000932']['notes'])

    def test_every_csv_is_rectangular(self):
        for p in [*(ROOT/'research').rglob('*.csv'), *(ROOT/'data').glob('china*.csv')]:
            with p.open(encoding='utf-8-sig',newline='') as f:
                rows=list(csv.reader(f))
            for n,row in enumerate(rows[1:],2):
                if row:self.assertEqual(len(row),len(rows[0]),f'{p}:{n}')

    def test_raw_prices_unchanged_from_research_baseline(self):
        manifest=json.loads((ROOT/'research/china_etf_review_20261102/unchanged_price_hashes.json').read_text(encoding='utf-8'))
        for name,digest in manifest.items():
            data=(ROOT/name).read_text(encoding='utf-8-sig').replace('\r\n','\n').encode()
            self.assertEqual(hashlib.sha256(data).hexdigest(),digest)

    def test_backup_repairs_preserve_original_fields(self):
        with (ROOT/'research/china_etf_review_20261102/original_backup_bdc4999.csv.txt').open(encoding='utf-8-sig',newline='') as f: old=list(csv.reader(f))
        fixed=read('research/backup_china_sector_representative_review_expanded.csv')
        self.assertEqual(len(fixed),15)
        for original,current in zip([r for r in old[1:] if r],fixed):
            if len(original)>len(old[0]):original=original[:16]+[','.join(original[16:-2])]+original[-2:]
            self.assertEqual([current[k] for k in old[0]],original)
            self.assertEqual(current['archive_status'],'historical_superseded_do_not_use_for_current_selection')

    def test_12_volumes_reproduce_snapshot(self):
        bars=read('data/china_candidate_prices.csv')
        for r in self.sel:
            series=sorted([b for b in bars if b['symbol']==r['symbol']],key=lambda b:b['date'])[-60:]
            self.assertEqual(series[0]['date'],r['volume_window_start'])
            self.assertEqual(series[-1]['date'],r['volume_window_end'])
            self.assertLess(abs(sum(float(b['volume']) for b in series)/60-float(r['avg_daily_volume_60d'])),0.5)

    def test_pair_correlations_reproduce_snapshot(self):
        bars=read('data/china_candidate_prices.csv')
        for a,b,expected in [('512700','512800',0.9827866854141801),('512480','512760',0.9950150819383523)]:
            maps=[]
            for symbol in [a,b]:
                seq=sorted([r for r in bars if r['symbol']==symbol],key=lambda r:r['date'])
                maps.append({curr['date']:float(curr['close'])/float(prev['close'])-1 for prev,curr in zip(seq,seq[1:])})
            dates=sorted(set(maps[0])&set(maps[1])); self.assertEqual(len(dates),298)
            x,y=[[m[d] for d in dates] for m in maps]
            mx,my=sum(x)/len(x),sum(y)/len(y)
            rho=sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
            self.assertAlmostEqual(rho,expected,places=10)

if __name__=='__main__':unittest.main()
