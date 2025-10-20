"""
Quick analysis script to verify D6 (MIDI 86) velocity assignments.
Run this after auto-assign to check if monotonicity is maintained.
"""
import json
import sys


def analyze_d6_mapping(session_file="sessions/session-VintageV3.json"):
    """Analyze D6 (MIDI 86) velocity layer assignments."""

    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Session file not found: {session_file}")
        return False

    samples_cache = data.get('samples_cache', {})
    mapping = data.get('mapping', {})

    # Get D6 (MIDI 86) mappings
    d6_mappings = [(k, v) for k, v in mapping.items() if k.startswith('86,')]

    if not d6_mappings:
        print("No D6 (MIDI 86) mappings found!")
        return False

    print("=" * 80)
    print("D6 (MIDI 86) Velocity Layer Analysis")
    print("=" * 80)
    print(f"Total D6 mappings: {len(d6_mappings)}")
    print()

    # Collect velocity layer assignments
    assignments = []
    for key, sample_id in sorted(d6_mappings):
        midi, vel = key.split(',')
        vel = int(vel)
        sample = samples_cache.get(sample_id)

        if sample:
            vel_amp = sample.get('velocity_amplitude', 0)
            filename = sample.get('filename', 'Unknown')
            assignments.append((vel, vel_amp, filename))
        else:
            print(f"WARNING: Layer {vel} - Sample ID not found in cache!")
            assignments.append((vel, None, 'MISSING'))

    # Display assignments
    print("Velocity Layer Assignments:")
    print("-" * 80)
    for vel, amp, filename in assignments:
        if amp is not None:
            print(f"Layer {vel}: vel_amp={amp:.5f} | {filename}")
        else:
            print(f"Layer {vel}: MISSING SAMPLE")
    print()

    # Check monotonicity
    print("Monotonicity Check:")
    print("-" * 80)
    monotonic = True
    for i in range(1, len(assignments)):
        prev_vel, prev_amp, _ = assignments[i-1]
        curr_vel, curr_amp, _ = assignments[i]

        if prev_amp is None or curr_amp is None:
            continue

        if curr_amp >= prev_amp:
            status = "PASS"
        else:
            status = "FAIL"
            monotonic = False

        print(f"Layer {prev_vel} ({prev_amp:.5f}) <= Layer {curr_vel} ({curr_amp:.5f}): {status}")

    print()
    print("=" * 80)
    if monotonic:
        print("SUCCESS: All monotonicity checks PASSED!")

        # Verify extremes
        if assignments:
            first_amp = assignments[0][1]
            last_amp = assignments[-1][1]

            # Get all D6 samples
            all_d6 = [(sid, s['velocity_amplitude'])
                     for sid, s in samples_cache.items()
                     if s.get('detected_midi') == 86]
            all_amps = [amp for _, amp in all_d6]

            if all_amps:
                min_amp = min(all_amps)
                max_amp = max(all_amps)

                print(f"Layer 0 has amplitude: {first_amp:.5f} (min available: {min_amp:.5f})")
                print(f"Layer {len(assignments)-1} has amplitude: {last_amp:.5f} (max available: {max_amp:.5f})")

                if last_amp == max_amp:
                    print("  Highest layer correctly assigned LOUDEST sample!")
    else:
        print("FAILURE: Monotonicity violations detected!")
    print("=" * 80)

    return monotonic


if __name__ == "__main__":
    session_file = sys.argv[1] if len(sys.argv) > 1 else "sessions/session-VintageV3.json"
    success = analyze_d6_mapping(session_file)
    sys.exit(0 if success else 1)
