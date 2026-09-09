# UK Road Safety: Exploratory Data Analysis

An end-to-end analysis of reported personal-injury road collisions and casualties in Great Britain during 2025. The project follows the **PACE** framework: Plan, Analyse, Construct and Execute.

## Business question

Which temporal, environmental, road and demographic factors are associated with more severe reported road collisions and casualties?

## Project highlights

- Combines the official 2025 collision and casualty CSV files
- Validates identifiers, missing data, coordinates, ages and duplicate records
- Decodes official STATS19 category codes into readable labels
- Engineers month, weekday, hour, time period, weekend and age-group features
- Uses percentage-based severity comparisons to avoid misleading raw-count conclusions
- Examines time, speed limit, lighting, weather, road surface and road-user groups
- Includes a geographic hotspot visualisation
- Produces a dynamic executive summary and responsible recommendations

## Repository structure

```text
uk-road-safety-eda/
├── uk_road_safety_eda.ipynb
├── README.md
├── requirements.txt
├── LICENSE
├── .gitignore
├── data/
│   └── README.md
└── images/
    └── .gitkeep
```

## Run in Google Colab

1. Download the 2025 **Collisions** and **Casualties** CSV files from the [DfT Road Safety Open Data page](https://www.gov.uk/government/statistical-data-sets/road-safety-open-data).
2. Open `uk_road_safety_eda.ipynb` in Google Colab.
3. Upload both CSV files to the Colab session and keep these original filenames:
   - `dft-road-casualty-statistics-collision-2025.csv`
   - `dft-road-casualty-statistics-casualty-2025.csv`
4. Select **Runtime > Run all**.

The notebook follows the course exemplars and loads each file directly with `pd.read_csv("filename.csv")`.

## Data source

Department for Transport, **Road Safety Open Data, 2025**. The data contains personal-injury collisions reported to the police on public roads in Great Britain. It does not represent every collision that occurred.

- [Official data and downloads](https://www.gov.uk/government/statistical-data-sets/road-safety-open-data)
- [STATS19 data guide](https://www.gov.uk/government/statistical-data-sets/road-safety-open-data#guidance-and-documentation)

Available under the Open Government Licence v3.0.

## Important interpretation notes

- Association does not prove causation.
- Raw collision counts are affected by population, traffic volume and exposure.
- Police reporting and recording practices affect the dataset.
- Severity comparisons use within-group percentages wherever appropriate.
- Unknown codes are retained as `Unknown` rather than silently removed.

## Tools

Python, pandas, NumPy, Matplotlib, Seaborn, Jupyter and Google Colab.
