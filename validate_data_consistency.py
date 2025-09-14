import pandas as pd
import sys
from pathlib import Path


def check_zero_after_nonzero(group, field_name, tif_name):
    """Check if a field has zero values after the first non-zero value."""
    results = []

    # Find the earliest year with ANY non-zero value (positive or negative)
    non_zero_mask = group[field_name] != 0
    if non_zero_mask.any():
        first_nonzero_idx = non_zero_mask.idxmax()

        # Check for zeros in subsequent years (negative values are okay, only flag zeros)
        subsequent_data = group.loc[first_nonzero_idx + 1 :]
        zero_mask = subsequent_data[field_name] == 0

        # For fund_balance_end, exclude zeros that are the very last data point
        if field_name == "fund_balance_end" and zero_mask.any():
            zero_indices = zero_mask[zero_mask].index
            zero_indices = [idx for idx in zero_indices if idx != group.index[-1]]
            zero_mask = pd.Series(False, index=zero_mask.index)
            for idx in zero_indices:
                zero_mask.loc[idx] = True

        if zero_mask.any():
            years = subsequent_data.loc[zero_mask, "tif_year"].tolist()
            results.append(
                {"tif_name": tif_name, "years": years, "discrepancy_field": field_name}
            )

    return results


def _numeric_equal(a, b, tol=1e-6):
    """Compare numeric values robustly. If both are integer-like, compare ints."""
    if pd.isna(a) or pd.isna(b):
        return False
    a_f = float(a)
    b_f = float(b)
    if abs(a_f - round(a_f)) < tol and abs(b_f - round(b_f)) < tol:
        return int(round(a_f)) == int(round(b_f))
    return abs(a_f - b_f) <= tol


def find_first_cumulative_mismatches(df, baseline_year=2010):
    """
    For each TIF and each cumulative field, find the FIRST year where:
      prev_reported_cumulative + current_yearly_value != current_reported_cumulative

    Baseline selection:
      - If the group has a row for baseline_year use that row's reported cumulative as the
        starting prev_cumulative.
      - Otherwise use the group's first available year as the baseline.
    Returns a list of discrepancy dicts (one entry per TIF+field when/if a mismatch is found).
    """
    pairs = [
        ("cumulative_property_tax_extraction", "property_tax_extraction"),
        ("cumulative_transfers_in", "transfers_in"),
    ]

    discrepancies = []

    for tif_name, group in df.groupby("tif_name"):
        g = group.sort_values("tif_year").reset_index(drop=True)
        g["tif_year"] = pd.to_numeric(g["tif_year"], errors="coerce")

        for cum_field, year_field in pairs:
            if cum_field not in g.columns or year_field not in g.columns:
                continue

            g[cum_field] = pd.to_numeric(g[cum_field], errors="coerce")
            g[year_field] = pd.to_numeric(g[year_field], errors="coerce")

            # pick baseline: prefer baseline_year if present, else first row
            baseline_idxs = g.index[g["tif_year"] == baseline_year].tolist()
            baseline_idx = baseline_idxs[0] if baseline_idxs else 0

            # get first non-null cumulative at/after baseline_idx
            prev_cum = None
            prev_year = None
            for i in range(baseline_idx, len(g)):
                if not pd.isna(g.at[i, cum_field]):
                    prev_cum = g.at[i, cum_field]
                    prev_year = int(g.at[i, "tif_year"])
                    baseline_idx = i
                    break

            if prev_cum is None:
                discrepancies.append(
                    {
                        "tif_name": tif_name,
                        "field": cum_field,
                        "first_bad_year": None,
                        "reported_cumulative": None,
                        "expected_cumulative": None,
                        "reason": "no baseline cumulative found (all null)",
                    }
                )
                continue

            # walk forward; break on first mismatch
            for i in range(baseline_idx + 1, len(g)):
                curr_year = int(g.at[i, "tif_year"])
                curr_cum = g.at[i, cum_field]
                curr_yearly = g.at[i, year_field]

                if pd.isna(curr_cum) or pd.isna(curr_yearly):
                    if not pd.isna(curr_cum):
                        prev_cum = curr_cum
                        prev_year = curr_year
                    continue

                expected = prev_cum + curr_yearly
                if not _numeric_equal(expected, curr_cum):
                    discrepancies.append(
                        {
                            "tif_name": tif_name,
                            "field": cum_field,
                            "first_bad_year": curr_year,
                            "reported_cumulative": curr_cum,
                            "expected_cumulative": expected,
                            "prev_year": prev_year,
                            "prev_reported_cumulative": prev_cum,
                            "yearly_value": curr_yearly,
                        }
                    )
                    break  # only first mismatch per tif/field

                prev_cum = curr_cum
                prev_year = curr_year

    return discrepancies


def main():
    # Get year from command line argument
    if len(sys.argv) < 2:
        print("Usage: python validate_data_consistency.py <year>")
        sys.exit(1)

    year = sys.argv[1]
    output_dir = Path(f"C:/Users/w/clonedGitRepos/chi-tif-parser/csvs/{year}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{year}_validate_data_consistency.csv"

    # Load CSV
    file_path = r"C:\Users\w\clonedGitRepos\chi-tif-parser\csvs\chi_tif_data_master.csv"
    df = pd.read_csv(file_path)

    # Ensure proper types
    numeric_cols = [
        "tif_year",
        "property_tax_extraction",
        "fund_balance_end",
    ]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    # Sort data by TIF and year
    df = df.sort_values(["tif_name", "tif_year"])

    # --- cumulative check: first bad year per TIF/field ---
    cum_discrepancies = find_first_cumulative_mismatches(df, baseline_year=2010)

    if cum_discrepancies:
        print("Cumulative consistency check FAILED (first bad year per TIF/field):")
        for d in cum_discrepancies:
            if d.get("first_bad_year") is None:
                print(
                    f"{d['tif_name']} {d['field']}: unable to validate - {d.get('reason')}"
                )
            else:
                print(
                    f"{d['tif_name']} {d['field']}: failed at {d['first_bad_year']} "
                    f"(reported={d['reported_cumulative']}, expected={d['expected_cumulative']})"
                )

        cum_report_path = output_dir / f"{year}_cumulative_discrepancies.csv"
        pd.DataFrame(cum_discrepancies).to_csv(cum_report_path, index=False)
        print(f"Saved cumulative discrepancy report to: {cum_report_path}")

        sys.exit(1)
    # -----------------------------------------------------

    # Define fields to check
    fields_to_check = ["property_tax_extraction", "fund_balance_end"]

    all_results = []

    for tif_name, group in df.groupby("tif_name"):
        group = group.reset_index(drop=True)
        for field in fields_to_check:
            results = check_zero_after_nonzero(group, field, tif_name)
            all_results.extend(results)

    # Output results to console
    print("TIFs with zero values after first non-zero year:")
    for entry in all_results:
        print(
            f"{entry['tif_name']} ({entry['discrepancy_field']}): Years -> {entry['years']}"
        )

    # Create CSV report
    report_data = []
    for entry in all_results:
        years_str = ", ".join(map(str, entry["years"]))
        report_data.append(
            {
                "tif_name": entry["tif_name"],
                "years": years_str,
                "discrepancy_field": entry["discrepancy_field"],
                "status": "",  # Placeholder for manual review status
            }
        )

    report_df = pd.DataFrame(report_data)
    if not report_df.empty:
        report_df = report_df.sort_values(
            by=["tif_name", "discrepancy_field"], ascending=True
        ).reset_index(drop=True)
    report_df.to_csv(output_file, index=False)

    print(f"\nCSV report saved to: {output_file}")
    print(f"Total discrepancies found: {len(all_results)}")


if __name__ == "__main__":
    main()
