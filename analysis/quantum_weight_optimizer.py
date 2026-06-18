# analysis/quantum_weight_optimizer.py
import numpy as np
import json
from scipy.stats import spearmanr

class QuantumWeightOptimizer:
    def __init__(self, features, forward_returns, n_iter=5000, temp_init=100.0, temp_min=0.01, cooling_rate=0.995):
        self.features = np.array(features)
        self.forward_returns = np.array(forward_returns)
        self.n_features = features.shape[1]
        self.n_iter = n_iter
        self.temp_init = temp_init
        self.temp_min = temp_min
        self.cooling_rate = cooling_rate

        # Normalize features
        self.features = (self.features - np.mean(self.features, axis=0)) / (np.std(self.features, axis=0) + 1e-8)
        self.feature_names = ['rev_growth', 'pat_growth', 'ebitda_margin', 'pat_margin', 'eps', 'pe_ratio', 'div_yield', 'price_return']

    def _objective(self, weights):
        scores = np.dot(self.features, weights)
        corr, _ = spearmanr(scores, self.forward_returns)
        return -corr if not np.isnan(corr) else 1000.0

    def _random_weights(self):
        w = np.random.rand(self.n_features)
        return w / np.sum(w)

    def _perturb(self, weights, step=0.05):
        new_w = weights + np.random.normal(0, step, self.n_features)
        new_w = np.clip(new_w, 0.0, 1.0)
        if np.sum(new_w) > 0:
            return new_w / np.sum(new_w)
        return self._random_weights()

    def optimize(self):
        current_w = self._random_weights()
        current_energy = self._objective(current_w)
        best_w = current_w.copy()
        best_energy = current_energy
        temp = self.temp_init

        print(f"🔬 Quantum-Inspired Annealing Optimization started.")
        print(f"   Features: {self.n_features}, Samples: {len(self.forward_returns)}")
        print(f"   Initial IC = {abs(current_energy):.4f}")

        while temp > self.temp_min:
            for _ in range(self.n_iter):
                candidate_w = self._perturb(current_w)
                candidate_energy = self._objective(candidate_w)
                delta_e = candidate_energy - current_energy
                if delta_e < 0 or np.random.rand() < np.exp(-delta_e / temp):
                    current_w = candidate_w
                    current_energy = candidate_energy
                if current_energy < best_energy:
                    best_w = current_w.copy()
                    best_energy = current_energy
            temp *= self.cooling_rate

        print(f"✅ Optimized. IC = {abs(best_energy):.4f}")
        weight_dict = {}
        for name, w in zip(self.feature_names, best_w):
            weight_dict[name] = round(float(w), 4)
            print(f"   - {name}: {weight_dict[name]:.4f}")
        with open('weights.json', 'w') as f:
            json.dump(weight_dict, f, indent=2)
        return weight_dict

if __name__ == "__main__":
    # Demo with synthetic data
    np.random.seed(42)
    X = np.random.randn(500, 8)
    y = (0.3 * X[:, 0] + 0.2 * X[:, 1] + 0.1 * X[:, 2] - 0.1 * X[:, 5] + 0.2 * np.random.randn(500))
    y = y / np.std(y)
    opt = QuantumWeightOptimizer(X, y, n_iter=2000)
    opt.optimize()
