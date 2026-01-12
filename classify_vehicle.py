#!/usr/bin/env python3
"""
Runtime inference module for vehicle classification.
DEPRECATED: This module is kept for backward compatibility.
Please use: from vehicle_classifier import VehicleClassifier

This file will be removed in a future version.
"""

# Try to import from the library first, fallback to local implementation
try:
    from vehicle_classifier import VehicleClassifier
except ImportError:
    # Fallback: local implementation (kept for backward compatibility)
    import json
    from pathlib import Path
    from typing import Dict, List, Optional, Tuple
    
    import numpy as np
    
    
    class VehicleClassifier:
        """Simple statistical classifier for vehicle identification."""
        
        def __init__(self, summary_file: str = "data/classifier_summary.json"):
            """Load classifier summary from JSON file."""
            self.summary = {}
            summary_path = Path(summary_file)
            
            if summary_path.exists():
                with open(summary_path, "r") as f:
                    self.summary = json.load(f)
            else:
                raise FileNotFoundError(f"Classifier summary not found: {summary_file}")
        
        def extract_features(self, power_samples: List[float]) -> Optional[Dict[str, float]]:
            """
            Extract features from power samples.
            
            Robust to:
            - Partial captures (no full ramp visible)
            - Anomalies (dips, spikes)
            - Different capture window sizes
            """
            if not power_samples or len(power_samples) < 2:
                return None
            
            arr = np.array(power_samples)
            
            # Filter to active charging (>= 0.5 kW)
            active = arr[arr >= 0.5]
            
            if len(active) < 1:
                active = arr[arr > 0]
            
            if len(active) < 1:
                return None
            
            mean_power = float(np.mean(active))
            std_power = float(np.std(active))
            cv = std_power / mean_power if mean_power > 0 else 0.0
            
            return {
                "mean_power_kw": mean_power,
                "cv_stability": float(cv),
            }
        
        def predict(self, power_samples: List[float]) -> Tuple[Optional[str], float]:
            """
            Predict vehicle from power samples.
            
            Returns:
                (vehicle_name, confidence_0_to_1)
            """
            features = self.extract_features(power_samples)
            if features is None:
                return None, 0.0
            
            mean_power = features["mean_power_kw"]
            
            # Compute distance to each vehicle's mean power
            distances = {}
            for vehicle, stats in self.summary.items():
                vehicle_mean = stats["mean_power"]["mean"]
                vehicle_std = stats["mean_power"].get("std", 0.1)
                
                if vehicle_std > 0:
                    distance = abs(mean_power - vehicle_mean) / vehicle_std
                else:
                    distance = abs(mean_power - vehicle_mean)
                
                distances[vehicle] = distance
            
            if not distances:
                return None, 0.0
            
            # Best match = smallest distance
            best_vehicle = min(distances, key=distances.get)
            best_distance = distances[best_vehicle]
            worst_distance = max(distances.values())
            
            # Confidence based on margin
            if worst_distance > 0:
                confidence = (worst_distance - best_distance) / worst_distance
            else:
                confidence = 0.0
            
            return best_vehicle, float(confidence)


if __name__ == "__main__":
    # Quick test
    import sys
    
    classifier = VehicleClassifier()
    
    # Simulate a 5-min capture: steady-state Equinox (9.0 kW)
    test_samples = [9.0, 9.02, 9.01, 8.98, 9.03, 9.0] * 5
    
    vehicle, conf = classifier.predict(test_samples)
    print(f"Predicted: {vehicle} (confidence: {conf:.2%})")
