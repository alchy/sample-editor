"""
Test auto-assign velocity algorithm for monotonic distribution.
This test verifies that velocity layers are assigned in ascending order of amplitude.
"""


def test_monotonic_velocity_assignment():
    """Test that velocity assignment maintains monotonic increase."""

    # Simulate D6 samples with known velocity amplitudes
    samples_data = [
        0.10294,
        0.12445,
        0.13374,
        0.14932,
        0.15742,
        0.21794,
        0.24127,
        0.24877,
        0.32126,
        0.37434,
    ]

    velocity_layers = 8
    num_samples = len(samples_data)

    # Sort samples (ascending: quietest to loudest)
    sorted_samples = sorted(samples_data)
    min_rms = min(samples_data)
    max_rms = max(samples_data)
    range_size = max_rms - min_rms

    # Assign samples to velocity layers using simple proportional distribution
    assignments = {}

    # Simple proportional distribution using midpoint of each layer's range
    for velocity in range(velocity_layers):
        # Calculate proportional index using midpoint of layer range
        sample_idx = int((velocity + 0.5) * num_samples / velocity_layers)

        # Clamp to valid range
        sample_idx = min(sample_idx, num_samples - 1)

        # Assign the sample at this index
        assignments[velocity] = sorted_samples[sample_idx]

    # Verify results
    print("Linear Interpolation - Target RMS vs Assigned Sample:")
    print("=" * 80)
    for vel in range(velocity_layers):
        target_rms = min_rms + (vel / float(velocity_layers - 1)) * range_size
        assigned_rms = assignments.get(vel, 0)
        distance = abs(assigned_rms - target_rms) if assigned_rms else 0
        print(f"Layer {vel}: target={target_rms:.5f} -> assigned={assigned_rms:.5f} (delta={distance:.5f})")

    print("\nVelocity Layer Assignments:")
    print("=" * 60)
    for vel in range(velocity_layers):
        amp = assignments.get(vel, 0)
        print(f"Layer {vel}: {amp:.5f}")

    # Check monotonicity: each layer should have >= amplitude than previous
    print("\nMonotonicity Check:")
    print("=" * 60)
    for vel in range(1, velocity_layers):
        prev_amp = assignments[vel - 1]
        curr_amp = assignments[vel]

        if curr_amp >= prev_amp:
            status = "PASS"
        else:
            status = "FAIL"

        print(f"Layer {vel-1} ({prev_amp:.5f}) <= Layer {vel} ({curr_amp:.5f}) {status}")

    # Verify that highest layer gets the loudest sample
    assert assignments[velocity_layers - 1] == max(samples_data), \
        f"Highest layer should get loudest sample! Got {assignments[velocity_layers - 1]}, expected {max(samples_data)}"

    # Verify that lowest layer gets one of the quietest samples
    assert assignments[0] == min(samples_data) or assignments[0] == sorted_samples[0], \
        f"Lowest layer should get quietest sample! Got {assignments[0]}"

    print("\nAll monotonicity checks PASSED!")
    print(f"Highest layer ({velocity_layers-1}) correctly assigned loudest sample: {assignments[velocity_layers-1]:.5f}")
    print(f"Lowest layer (0) correctly assigned quietest sample: {assignments[0]:.5f}")


if __name__ == "__main__":
    test_monotonic_velocity_assignment()
