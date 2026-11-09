import sys
import math
LEGAL_STEER = 12000
LEGAL_DRIVES = 34000
LEGAL_TANDEMS = 34000
LEGAL_GROSS = 80000
def calculate_tandem_shift(steer, drives, tandems, hole_spacing_inches=4):
    gross = steer + drives + tandems
    print("\n" + "=" * 50)
    print(" ⚖️  CAT SCALE AUDIT & TANDEM SLIDE ANALYSIS")
    print("=" * 50)
    print(f"Current Weights: Steer: {steer:,} lbs | Drives: {drives:,} lbs | Tandems: {tandems:,} lbs")
    print(f"Gross Vehicle Weight: {gross:,} lbs")
    if gross > LEGAL_GROSS:
        over_gross = gross - LEGAL_GROSS
        print(f"\n⚠️  OVERWEIGHT VIOLATION: Gross is over legal limit by {over_gross:,} lbs!")
        print("   You cannot balance this out with a tandem slide. Return to shipper for rework.")
        return
    drive_over = drives - LEGAL_DRIVES
    tandem_over = tandems - LEGAL_TANDEMS
    if drive_over <= 0 and tandem_over <= 0 and steer <= LEGAL_STEER:
        print("\n✅ All axle groups and gross weight are legally compliant!")
    else:
        if drive_over > 0:
            print(f"\n⚠️  Drives are OVER legal limit by {drive_over:,} lbs.")
        if tandem_over > 0:
            print(f"\n⚠️  Tandems are OVER legal limit by {tandem_over:,} lbs.")
        if steer > LEGAL_STEER:
            print(f"\n⚠️  Steer axle is over standard 12,000 lbs by {steer - LEGAL_STEER:,} lbs (check tire ratings).")
    weight_difference = drives - tandems
    transfer_needed = abs(weight_difference) // 2
    lbs_per_hole = 450 if hole_spacing_inches == 6 else 300
    holes = math.ceil(transfer_needed / lbs_per_hole)
    print("\n--- Adjustment Plan ---")
    if weight_difference > 0:
        print(f"• Target Transfer: Shift ~{transfer_needed:,} lbs off the drives onto the tandems.")
        print(f"• Action: Slide trailer tandems **FORWARD** (toward the cab) approx {holes} hole(s).")
        print(f"• Expected Result: Drives: ~{drives - (holes * lbs_per_hole):,} lbs | Tandems: ~{tandems + (holes * lbs_per_hole):,} lbs")
    elif weight_difference < 0:
        print(f"• Target Transfer: Shift ~{transfer_needed:,} lbs off the tandems onto the drives.")
        print(f"• Action: Slide trailer tandems **BACK** (toward the rear doors) approx {holes} hole(s).")
        print(f"• Expected Result: Drives: ~{drives + (holes * lbs_per_hole):,} lbs | Tandems: ~{tandems - (holes * lbs_per_hole):,} lbs")
    else:
        print("• Drives and tandems are already evenly balanced.")
    print(f"\n(Calculated using standard {hole_spacing_inches}\" pin spacing at ~{lbs_per_hole} lbs/hole. Always re-scale after pinning.)")
    print("=" * 50 + "\n")
