import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "cells": [],
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
        "colab": {"name": "uk_road_safety_eda.ipynb", "provenance": []},
    },
}


def md(text):
    nb["cells"].append({"cell_type": "markdown", "metadata": {}, "source": text.strip().splitlines(keepends=True)})


def code(text):
    nb["cells"].append({
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": text.strip().splitlines(keepends=True),
    })


md("""
# UK Road Safety: Exploratory Data Analysis

**Portfolio project | Transport analytics | Great Britain, 2025**

This project explores temporal, environmental, road and demographic patterns in personal-injury road collisions reported to the police. It follows the **PACE** framework: Plan, Analyse, Construct and Execute.

> The analysis identifies associations, not causes. Counts are also influenced by exposure: a road, time or group with more travel may naturally record more collisions.
""")

md("""
## PACE: Plan

### Stakeholder scenario

A road-safety policy team wants an accessible overview of when and where serious collisions occur, which road users are most affected, and which conditions deserve deeper investigation.

### Primary question

**Which temporal, environmental, road and demographic factors are associated with more severe reported road collisions and casualties?**

### Supporting questions

1. How do collision counts and severity vary by month, weekday and hour?
2. How does the serious-or-fatal share differ by speed limit, lighting, weather and road surface?
3. Which road-user and age groups have the highest serious-or-fatal casualty shares?
4. Where are reported collision concentrations visible geographically?

### Success criteria

- Join collisions and casualties without duplicating or losing records unexpectedly.
- Decode official category codes into readable labels.
- Prefer within-group severity percentages over misleading raw-count comparisons.
- Retain and clearly label unknown values.
- Finish with evidence-based findings, limitations and recommendations.
""")

code("""
import re
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.max_columns", 60)
pd.set_option("display.float_format", lambda x: f"{x:,.2f}")

sns.set_theme(style="whitegrid", context="notebook")
BLUE = "#2563EB"
ORANGE = "#F59E0B"
RED = "#DC2626"
GREEN = "#059669"
""")

md("""
## PACE: Analyse

### Load the two CSV files

Upload the two 2025 CSV files to Colab without changing their downloaded filenames. As in the course exemplars, each dataset is loaded with one direct `pd.read_csv()` statement.
""")

code("""
def standardise_columns(columns):
    cleaned = []
    for name in columns:
        name = str(name).strip().lower()
        name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
        cleaned.append(name)
    return cleaned

collisions = pd.read_csv("dft-road-casualty-statistics-collision-2025.csv")
casualties = pd.read_csv("dft-road-casualty-statistics-casualty-2025.csv")

collisions.columns = standardise_columns(collisions.columns)
casualties.columns = standardise_columns(casualties.columns)

# Support releases that still use the older 'accident' terminology.
collisions = collisions.rename(columns={
    "accident_index": "collision_index",
    "accident_reference": "collision_reference",
    "accident_year": "collision_year",
    "accident_severity": "collision_severity",
})
casualties = casualties.rename(columns={
    "accident_index": "collision_index",
    "accident_reference": "collision_reference",
    "accident_year": "collision_year",
})

print(f"Collision rows: {len(collisions):,}")
print(f"Casualty rows:  {len(casualties):,}")
display(collisions.head())
display(casualties.head())
""")

md("""
### Data quality assessment

The collision identifier should be unique in the collision table. A collision may have several casualty rows, so it is expected to repeat in the casualty table.
""")

code("""
def quality_report(data):
    return pd.DataFrame({
        "dtype": data.dtypes.astype(str),
        "missing": data.isna().sum(),
        "missing_pct": data.isna().mean().mul(100).round(2),
        "unique": data.nunique(dropna=True),
    }).sort_values("missing_pct", ascending=False)

print("Collision data quality")
display(quality_report(collisions).head(20))
print("Casualty data quality")
display(quality_report(casualties).head(20))
""")

code("""
collision_duplicates = collisions.duplicated().sum()
casualty_duplicates = casualties.duplicated().sum()
duplicate_collision_ids = collisions["collision_index"].duplicated().sum()
unmatched_casualties = (~casualties["collision_index"].isin(collisions["collision_index"])).sum()

print(f"Exact duplicate collision rows: {collision_duplicates:,}")
print(f"Exact duplicate casualty rows: {casualty_duplicates:,}")
print(f"Duplicate IDs in collision table: {duplicate_collision_ids:,}")
print(f"Casualties without a matching collision: {unmatched_casualties:,}")
""")

md("""
### Clean types and engineer time features
""")

code("""
collisions = collisions.drop_duplicates().copy()
casualties = casualties.drop_duplicates().copy()

collisions["date"] = pd.to_datetime(collisions["date"], dayfirst=True, errors="coerce")
collisions["hour"] = pd.to_numeric(
    collisions["time"].astype("string").str.extract(r"^(\\d{1,2})")[0],
    errors="coerce",
)

collisions["month"] = collisions["date"].dt.month_name()
collisions["month_number"] = collisions["date"].dt.month
collisions["day_name"] = collisions["date"].dt.day_name()
collisions["day_number"] = collisions["date"].dt.dayofweek
collisions["is_weekend"] = collisions["day_number"] >= 5
collisions["time_period"] = pd.cut(
    collisions["hour"],
    bins=[-1, 4, 11, 16, 20, 23],
    labels=["Night", "Morning", "Afternoon", "Evening", "Late night"],
)

for col in ["age_of_casualty", "casualty_severity", "sex_of_casualty", "casualty_class", "casualty_type"]:
    if col in casualties:
        casualties[col] = pd.to_numeric(casualties[col], errors="coerce")

casualties["age_valid"] = casualties["age_of_casualty"].where(casualties["age_of_casualty"].between(0, 110))
casualties["age_group"] = pd.cut(
    casualties["age_valid"],
    bins=[-1, 15, 24, 34, 44, 54, 64, 74, np.inf],
    labels=["0-15", "16-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75+"],
)
""")

md("""
### Decode important STATS19 fields

The raw data uses numerical codes. The mappings below cover the variables used in this analysis. Unexpected and missing codes are labelled `Unknown` rather than discarded.
""")

code("""
MAPS = {
    "collision_severity": {1: "Fatal", 2: "Serious", 3: "Slight"},
    "casualty_severity": {1: "Fatal", 2: "Serious", 3: "Slight"},
    "sex_of_casualty": {1: "Male", 2: "Female", 9: "Unknown"},
    "casualty_class": {1: "Driver or rider", 2: "Passenger", 3: "Pedestrian"},
    "urban_or_rural_area": {1: "Urban", 2: "Rural", 3: "Unallocated"},
    "light_conditions": {
        1: "Daylight", 4: "Darkness - lights lit", 5: "Darkness - lights unlit",
        6: "Darkness - no lighting", 7: "Darkness - lighting unknown",
    },
    "weather_conditions": {
        1: "Fine, no high winds", 2: "Raining, no high winds", 3: "Snowing, no high winds",
        4: "Fine with high winds", 5: "Raining with high winds", 6: "Snowing with high winds",
        7: "Fog or mist", 8: "Other", 9: "Unknown",
    },
    "road_surface_conditions": {
        1: "Dry", 2: "Wet or damp", 3: "Snow", 4: "Frost or ice", 5: "Flood",
        6: "Oil or diesel", 7: "Mud", 9: "Unknown",
    },
}

def decode(data, column):
    if column not in data:
        return
    numeric = pd.to_numeric(data[column], errors="coerce")
    data[f"{column}_label"] = numeric.map(MAPS[column]).fillna("Unknown")

for col in ["collision_severity", "urban_or_rural_area", "light_conditions", "weather_conditions", "road_surface_conditions"]:
    decode(collisions, col)

for col in ["casualty_severity", "sex_of_casualty", "casualty_class"]:
    decode(casualties, col)

collisions["serious_or_fatal"] = collisions["collision_severity"].isin([1, 2])
casualties["serious_or_fatal"] = casualties["casualty_severity"].isin([1, 2])
""")

code("""
collision_summary = pd.Series({
    "Reported collisions": len(collisions),
    "Casualties": len(casualties),
    "Fatal collisions": (collisions["collision_severity"] == 1).sum(),
    "Serious collisions": (collisions["collision_severity"] == 2).sum(),
    "Slight collisions": (collisions["collision_severity"] == 3).sum(),
    "Serious-or-fatal collision share (%)": collisions["serious_or_fatal"].mean() * 100,
})
collision_summary.to_frame("value")
""")

md("""
## PACE: Construct

### Collision severity overview
""")

code("""
severity_order = ["Fatal", "Serious", "Slight"]
severity_counts = collisions["collision_severity_label"].value_counts().reindex(severity_order).fillna(0)

fig, ax = plt.subplots(figsize=(8, 5))
sns.barplot(x=severity_counts.index, y=severity_counts.values, palette=[RED, ORANGE, BLUE], ax=ax)
ax.set_title("Most reported injury collisions are classified as slight", loc="left", weight="bold")
ax.set_xlabel("")
ax.set_ylabel("Reported collisions")
for container in ax.containers:
    ax.bar_label(container, fmt="{:,.0f}")
plt.tight_layout()
plt.show()
""")

md("""
### Time patterns
""")

code("""
month_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
monthly = collisions.groupby("month").agg(
    collisions=("collision_index", "size"),
    serious_or_fatal_share=("serious_or_fatal", "mean"),
).reindex(month_order).reset_index()
monthly["serious_or_fatal_share"] *= 100

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.lineplot(data=monthly, x="month", y="collisions", marker="o", color=BLUE, ax=axes[0])
sns.lineplot(data=monthly, x="month", y="serious_or_fatal_share", marker="o", color=RED, ax=axes[1])
axes[0].set_title("Reported collisions by month", loc="left", weight="bold")
axes[1].set_title("Serious-or-fatal share by month", loc="left", weight="bold")
for ax in axes:
    ax.tick_params(axis="x", rotation=55)
    ax.set_xlabel("")
axes[0].set_ylabel("Collisions")
axes[1].set_ylabel("Serious or fatal (%)")
plt.tight_layout()
plt.show()
""")

code("""
day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
hour_day = pd.crosstab(collisions["day_name"], collisions["hour"]).reindex(day_order)

plt.figure(figsize=(14, 5))
sns.heatmap(hour_day, cmap="Blues")
plt.title("Reported collisions by weekday and hour", loc="left", weight="bold")
plt.xlabel("Hour of day")
plt.ylabel("")
plt.tight_layout()
plt.show()
""")

md("""
### Compare serious-or-fatal shares

Raw counts can be misleading when groups have different numbers of observations. The helper below calculates the percentage of records within each group that were classified as serious or fatal, while also showing the group size.
""")

code("""
def severity_share(data, group, minimum_records=100):
    result = (
        data.groupby(group, observed=False)
            .agg(records=("serious_or_fatal", "size"), serious_or_fatal_share=("serious_or_fatal", "mean"))
            .reset_index()
    )
    result["serious_or_fatal_share"] *= 100
    return result[result["records"] >= minimum_records].sort_values("serious_or_fatal_share", ascending=False)

comparison_fields = [
    "urban_or_rural_area_label", "light_conditions_label",
    "weather_conditions_label", "road_surface_conditions_label", "speed_limit",
]

for field in comparison_fields:
    if field in collisions:
        print(field.replace("_", " ").title())
        display(severity_share(collisions, field))
""")

code("""
plot_fields = [c for c in ["urban_or_rural_area_label", "light_conditions_label", "speed_limit"] if c in collisions]
fig, axes = plt.subplots(1, len(plot_fields), figsize=(6 * len(plot_fields), 5))
axes = np.atleast_1d(axes)

for ax, field in zip(axes, plot_fields):
    plot_data = severity_share(collisions, field).sort_values("serious_or_fatal_share")
    sns.barplot(data=plot_data, x="serious_or_fatal_share", y=field, color=ORANGE, ax=ax)
    ax.set_title(field.replace("_label", "").replace("_", " ").title(), loc="left", weight="bold")
    ax.set_xlabel("Serious or fatal (%)")
    ax.set_ylabel("")

plt.tight_layout()
plt.show()
""")

md("""
### Casualty patterns
""")

code("""
age_severity = severity_share(casualties.dropna(subset=["age_group"]), "age_group", minimum_records=50)
class_severity = severity_share(casualties, "casualty_class_label", minimum_records=50)

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
sns.barplot(data=age_severity, x="age_group", y="serious_or_fatal_share", color=BLUE, ax=axes[0])
sns.barplot(data=class_severity, x="casualty_class_label", y="serious_or_fatal_share", color=GREEN, ax=axes[1])
axes[0].set_title("Serious-or-fatal casualty share by age", loc="left", weight="bold")
axes[1].set_title("Serious-or-fatal share by casualty class", loc="left", weight="bold")
for ax in axes:
    ax.set_xlabel("")
    ax.set_ylabel("Serious or fatal (%)")
axes[1].tick_params(axis="x", rotation=20)
plt.tight_layout()
plt.show()
""")

md("""
### Join casualty and collision circumstances

The validated many-to-one merge adds road and environmental conditions to each casualty without changing the number of casualty records.
""")

code("""
collision_context_columns = [c for c in [
    "collision_index", "date", "month", "day_name", "hour", "time_period", "speed_limit",
    "urban_or_rural_area_label", "light_conditions_label", "weather_conditions_label",
    "road_surface_conditions_label", "latitude", "longitude",
] if c in collisions]

casualty_context = casualties.merge(
    collisions[collision_context_columns],
    on="collision_index",
    how="left",
    validate="many_to_one",
)

assert len(casualty_context) == len(casualties)
print(f"Joined casualty rows: {len(casualty_context):,}")
print(f"Rows missing collision context: {casualty_context['date'].isna().sum():,}")
casualty_context.head()
""")

md("""
### Geographic distribution

This is a concentration map, not a risk map. Areas with more residents, roads and traffic exposure may naturally have more reported collisions.
""")

code("""
geo = collisions.dropna(subset=["longitude", "latitude"]).copy()
geo = geo[geo["longitude"].between(-8.5, 2.5) & geo["latitude"].between(49, 61)]

plt.figure(figsize=(8, 10))
plt.hexbin(
    geo["longitude"], geo["latitude"], gridsize=90,
    cmap="inferno", bins="log", mincnt=1,
)
plt.colorbar(label="Log collision concentration")
plt.title("Geographic concentration of reported collisions", loc="left", weight="bold")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.tight_layout()
plt.show()
""")

md("""
## PACE: Execute

### Dynamic executive summary

The summary is generated from the current dataset so its statements remain tied to calculated results.
""")

code("""
peak_month = monthly.loc[monthly["collisions"].idxmax()]
highest_month_share = monthly.loc[monthly["serious_or_fatal_share"].idxmax()]
top_age = age_severity.iloc[0]
top_class = class_severity.iloc[0]

print("EXECUTIVE SUMMARY")
print("-" * 72)
print(f"The dataset contains {len(collisions):,} reported injury collisions and {len(casualties):,} casualties.")
print(f"{peak_month['month']} recorded the most collisions, while {highest_month_share['month']} had the highest serious-or-fatal collision share.")
print(f"The {top_age['age_group']} age group had the highest serious-or-fatal casualty share among age groups meeting the minimum record threshold.")
print(f"{top_class['casualty_class_label']} had the highest serious-or-fatal share among casualty classes.")
print("These are descriptive associations and should not be interpreted as proof of causation or risk without exposure data.")
""")

md("""
### Recommendations

1. **Prioritise rate-based follow-up analysis.** Combine collision counts with population, road mileage or traffic-volume exposure before ranking locations or groups by risk.
2. **Investigate high-severity periods.** Examine the months, hours and time periods with elevated serious-or-fatal percentages, not only those with the largest counts.
3. **Target vulnerable road users carefully.** Use casualty-class and age patterns to guide deeper analysis and intervention design.
4. **Review rural, speed and lighting interactions.** Analyse these factors together because individual comparisons may conceal confounding relationships.
5. **Preserve unknown categories.** Missing and unknown codes may reflect reporting processes and should be monitored rather than silently removed.

### Limitations

- Only personal-injury collisions reported to the police on public roads are included.
- Collision counts do not measure exposure or individual risk.
- Observational associations do not demonstrate causation.
- Police forces may differ in reporting and severity-recording practices.
- The analysis decodes the fields it uses; consult the official guide before extending it to other coded variables.
- Geographic concentration is not adjusted for population or traffic volume.

### Next steps

- Add the 2025 vehicle file to compare vehicle and driver characteristics.
- Join DfT traffic-volume data to calculate exposure-adjusted rates.
- Compare several years using the DfT five-year files.
- Create an interactive Power BI or Tableau dashboard with geographic and time filters.
""")

md("""
## Data source

- [Department for Transport: Road Safety Open Data](https://www.gov.uk/government/statistical-data-sets/road-safety-open-data)
- [Official guidance and data dictionary](https://www.gov.uk/government/statistical-data-sets/road-safety-open-data#guidance-and-documentation)

The 2025 files are the latest full-year final validated release available when this project was prepared. Data is available under the Open Government Licence v3.0.
""")

with (ROOT / "uk_road_safety_eda.ipynb").open("w", encoding="utf-8") as file:
    json.dump(nb, file, indent=1, ensure_ascii=False)

print(f"Created {ROOT / 'uk_road_safety_eda.ipynb'}")

kaggle_nb = deepcopy(nb)
kaggle_nb["metadata"].pop("colab", None)
kaggle_nb["cells"].insert(1, {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## Kaggle setup\n",
        "\n",
        "Add the two official CSV files to Kaggle as a dataset named `uk-road-safety-2025`, "
        "then attach that dataset to this notebook.\n",
    ],
})

for cell in kaggle_nb["cells"]:
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        source = source.replace(
            '"dft-road-casualty-statistics-collision-2025.csv"',
            '"/kaggle/input/uk-road-safety-2025/dft-road-casualty-statistics-collision-2025.csv"',
        )
        source = source.replace(
            '"dft-road-casualty-statistics-casualty-2025.csv"',
            '"/kaggle/input/uk-road-safety-2025/dft-road-casualty-statistics-casualty-2025.csv"',
        )
        cell["source"] = source.splitlines(keepends=True)

with (ROOT / "uk_road_safety_eda_kaggle.ipynb").open("w", encoding="utf-8") as file:
    json.dump(kaggle_nb, file, indent=1, ensure_ascii=False)
print(f"Created {ROOT / 'uk_road_safety_eda_kaggle.ipynb'}")
