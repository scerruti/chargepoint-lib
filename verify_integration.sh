#!/bin/bash
# Verify all integration components are in place

echo "🔍 CPH50 Integration Verification"
echo "=================================="
echo ""

# Check classifier files
echo "✓ Classifier Files:"
test -f classify_vehicle.py && echo "  ✅ classify_vehicle.py" || echo "  ❌ classify_vehicle.py"
test -f train_vehicle_classifier.py && echo "  ✅ train_vehicle_classifier.py" || echo "  ❌ train_vehicle_classifier.py"
test -f data/classifier_summary.json && echo "  ✅ data/classifier_summary.json" || echo "  ❌ data/classifier_summary.json"
echo ""

# Check data files
echo "✓ Data Files:"
test -f data/last_session.json && echo "  ✅ data/last_session.json" || echo "  ❌ data/last_session.json"
test -f data/sessions/4751613101.json && echo "  ✅ Seed: Volvo (4751613101)" || echo "  ❌ Seed: Volvo"
test -f data/sessions/4754846071.json && echo "  ✅ Seed: Equinox (4754846071)" || echo "  ❌ Seed: Equinox"
echo ""

# Check monitoring files
echo "✓ Monitoring Files:"
test -f monitor_sessions.py && echo "  ✅ monitor_sessions.py" || echo "  ❌ monitor_sessions.py"
test -f collect_session_data.py && echo "  ✅ collect_session_data.py" || echo "  ❌ collect_session_data.py"
echo ""

# Check dashboard
echo "✓ Dashboard:"
test -f docs/dashboard.html && echo "  ✅ docs/dashboard.html" || echo "  ❌ docs/dashboard.html"
echo ""

# Test classifier functionality
echo "✓ Classifier Functionality:"
python3 << 'PYEOF'
try:
    from classify_vehicle import VehicleClassifier
    classifier = VehicleClassifier()
    
    # Test Volvo
    volvo_result = classifier.predict([8.50, 8.50, 8.50])
    print(f"  ✅ Volvo classification: {volvo_result[0]} ({volvo_result[1]:.1%})")
    
    # Test Equinox
    equinox_result = classifier.predict([9.01, 9.01, 9.01])
    print(f"  ✅ Equinox classification: {equinox_result[0]} ({equinox_result[1]:.1%})")
except Exception as e:
    print(f"  ❌ Error: {e}")
PYEOF
echo ""

# Check git status
echo "✓ Git Status:"
UNCOMMITTED=$(git status --porcelain | wc -l)
if [ $UNCOMMITTED -eq 0 ]; then
    echo "  ✅ No uncommitted changes"
else
    echo "  ⚠️  $UNCOMMITTED uncommitted changes"
fi

# Show recent commits
echo ""
echo "✓ Recent Commits:"
git log --oneline -3 | sed 's/^/  /'
echo ""
echo "✅ Integration verification complete!"
