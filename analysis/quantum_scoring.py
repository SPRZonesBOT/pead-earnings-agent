# analysis/quantum_scoring.py
import numpy as np
import json
from collections import deque

class QuantumScorer:
    def __init__(self, lookback=50):
        self.lookback = lookback
        self.buffers = {
            'rev_growth': deque(maxlen=lookback),
            'pat_growth': deque(maxlen=lookback),
            'ebitda_margin': deque(maxlen=lookback),
            'pat_margin': deque(maxlen=lookback),
            'eps': deque(maxlen=lookback),
            'pe_ratio': deque(maxlen=lookback),
            'div_yield': deque(maxlen=lookback),
        }
        self.weights = self._load_weights()

    def _load_weights(self):
        try:
            with open('weights.json', 'r') as f:
                w = json.load(f)
            print("✅ Loaded Quantum-Optimized Weights.")
            return w
        except:
            print("⚠️ Using default weights (weights.json not found).")
            return {
                'rev_growth': 0.20, 'pat_growth': 0.20, 'ebitda_margin': 0.15,
                'pat_margin': 0.10, 'eps': 0.10, 'pe_ratio': 0.10,
                'div_yield': 0.05, 'price_return': 0.10
            }

    def add_observation(self, factors):
        for k in self.buffers:
            if k in factors:
                self.buffers[k].append(factors[k])

    def compute_zscore(self, value, key):
        buf = self.buffers[key]
        if len(buf) < 10:
            return 0.0
        mean = np.mean(buf)
        std = np.std(buf)
        return (value - mean) / std if std != 0 else 0.0

    def score(self, fin, qoq_rev, qoq_pat, yoy_rev, yoy_pat, price_return, prev_fin=None):
        rev_growth = (0.7 * qoq_rev + 0.3 * yoy_rev)
        pat_growth = (0.7 * qoq_pat + 0.3 * yoy_pat)
        ebitda_margin = fin.get('ebitda_margin', 0)
        pat_margin = fin.get('pat_margin', 0)
        eps = fin.get('eps', 0)
        pe = fin.get('pe_ratio', 0)
        div_yield = fin.get('div_yield', 0)

        factors = {
            'rev_growth': rev_growth,
            'pat_growth': pat_growth,
            'ebitda_margin': ebitda_margin,
            'pat_margin': pat_margin,
            'eps': eps,
            'pe_ratio': -pe if pe else 0,
            'div_yield': div_yield,
        }
        self.add_observation(factors)

        z_rev = self.compute_zscore(rev_growth, 'rev_growth')
        z_pat = self.compute_zscore(pat_growth, 'pat_growth')
        z_ebitda = self.compute_zscore(ebitda_margin, 'ebitda_margin')
        z_pat_margin = self.compute_zscore(pat_margin, 'pat_margin')
        z_eps = self.compute_zscore(eps, 'eps')
        z_pe = self.compute_zscore(-pe if pe else 0, 'pe_ratio')
        z_div = self.compute_zscore(div_yield, 'div_yield')

        w = self.weights
        composite = (w['rev_growth'] * z_rev +
                     w['pat_growth'] * z_pat +
                     w['ebitda_margin'] * z_ebitda +
                     w['pat_margin'] * z_pat_margin +
                     w['eps'] * z_eps +
                     w['pe_ratio'] * z_pe +
                     w['div_yield'] * z_div)

        price_bonus = w.get('price_return', 0.10) * min(max(price_return / 5.0, 0), 2)
        total = composite + price_bonus

        score = 50 * (1 + np.tanh(total / 2))
        score = min(max(score, 0), 100)

        return {
            'rev_growth': rev_growth,
            'pat_growth': pat_growth,
            'ebitda_margin': ebitda_margin,
            'pat_margin': pat_margin,
            'eps': eps,
            'pe_ratio': pe,
            'div_yield': div_yield,
            'price_return': price_return,
            'composite': composite,
            'total_score': score,
        }
