"""Reproduce the FSI 2023 descriptive analysis without modifying the workbook."""
import argparse
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import openpyxl

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path,
                        default=ROOT / 'reports/FSI_2023_Analysis.xlsx')
    args = parser.parse_args()
    workbook = openpyxl.load_workbook(args.input, data_only=True, read_only=True)
    sheet = workbook['Data'] if 'Data' in workbook.sheetnames else workbook.active
    records = list(sheet.values)
    header_index = next(i for i, row in enumerate(records) if row[0] == 'Country')
    headers = list(records[header_index][:16])
    rows = [list(row[:16]) for row in records[header_index + 1:] if row[0] is not None]
    workbook.close()
    if not rows or len(headers) != 16:
        raise ValueError('Expected FSI country, year, rank, total and 12 indicator fields.')
    missing = sum(value is None for row in rows for value in row)
    if missing:
        raise ValueError(f'Missing source fields: {missing}')
    numeric = all(isinstance(value, (int, float)) and not isinstance(value, bool)
                  for row in rows for value in row[3:])
    if not numeric:
        raise ValueError('Total and indicator scores must be numeric.')
    duplicates = sum(n - 1 for n in Counter((r[0], r[1]) for r in rows).values())
    invalid = sum(not 0 <= v <= 10 for r in rows for v in r[4:])
    mismatches = sum(abs(r[3] - sum(r[4:])) > 1e-8 for r in rows)
    years = sorted({r[1] for r in rows})
    if duplicates or invalid or mismatches or years != [2023]:
        raise ValueError(f'Validation failed: duplicates={duplicates}, invalid={invalid}, '
                         f'total mismatches={mismatches}, years={years}')
    ranked = sorted(rows, key=lambda row: row[3], reverse=True)
    means = sorted([(headers[i], statistics.mean(r[i] for r in rows))
                    for i in range(4, 16)], key=lambda pair: pair[1], reverse=True)
    summary = {'year': 2023, 'countries': len(rows), 'indicators': 12,
               'mean_total': statistics.mean(r[3] for r in rows),
               'median_total': statistics.median(r[3] for r in rows),
               'highest_country': ranked[0][0], 'highest_total': ranked[0][3],
               'lowest_country': ranked[-1][0], 'lowest_total': ranked[-1][3],
               'missing_fields': missing, 'duplicate_keys': duplicates,
               'invalid_indicator_scores': invalid, 'total_mismatches': mismatches}
    report_dir = ROOT / 'reports'
    report_dir.mkdir(exist_ok=True)
    (report_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    for name, header, body in [
        ('top_10.csv', ['Country', 'Total'], [(r[0], r[3]) for r in ranked[:10]]),
        ('indicator_means.csv', ['Indicator', 'Mean score'], means),
    ]:
        with (report_dir / name).open('w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerows(body)

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
    fig, axes = plt.subplots(1, 2, figsize=(16, 7.5), gridspec_kw={'wspace': .8})
    fig.suptitle('Fragile States Index 2023', fontsize=22, fontweight='bold',
                 x=.06, ha='left', color='#183B56')
    fig.text(.06, .90, f'{len(rows)} countries    |    Mean total: {summary["mean_total"]:.1f}/120'
             '    |    Higher scores indicate greater fragility', color='#506070')
    for ax, labels, values, xmax, title in [
        (axes[0], [r[0] for r in ranked[:10]], [r[3] for r in ranked[:10]],
         120, 'Highest total scores /120'),
        (axes[1], [name.split(': ', 1)[-1] for name, _ in means],
         [value for _, value in means], 10, 'Mean indicator scores /10'),
    ]:
        bars = ax.barh(labels, values, color='#2E75B6', height=.65)
        ax.invert_yaxis()
        ax.set_xlim(0, xmax)
        ax.set_title(title, loc='left', pad=16, fontweight='bold', color='#183B56')
        ax.bar_label(bars, labels=[f'{v:.1f}' for v in values], padding=5, fontsize=9)
        ax.spines[['top', 'right', 'left']].set_visible(False)
        ax.tick_params(axis='y', length=0)
        ax.xaxis.grid(True, alpha=.18)
        ax.set_axisbelow(True)
    fig.subplots_adjust(top=.81, bottom=.12, left=.18, right=.97)
    fig.text(.06, .035, 'Source: The Fund for Peace, FSI 2023. CC BY-NC-SA 4.0. '
             'Analysis: Mahad Buulle. Unweighted country averages.', fontsize=9, color='#506070')
    (ROOT / 'images').mkdir(exist_ok=True)
    fig.savefig(ROOT / 'images/overview.png', dpi=160, facecolor='white')
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
