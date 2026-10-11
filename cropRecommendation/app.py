'''
python3 -m venv .venv
source .venv/bin/activate #whenever you open new terminal
python -m pip install -r requirements.txt
'''

import sys
from pathlib import Path
import pandas as pd
import numpy as np

from flask import Flask, render_template, request
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import euclidean_distances

# Add project root directory to path to import from PricePrediction folder
sys.path.append(str(Path(__file__).parent))
from priceprediction import get_crop_price_forecast

app = Flask(
    __name__,
    template_folder="web",
    static_folder="web",
    static_url_path="/static"
)

# Load and clean the dataset
data = pd.read_csv("../cropRecommendation/crop_recommendation.csv")
data.columns = data.columns.str.strip()

features = ["K", "P", "Mg", "C"]
required_columns = ["label", "pHL", "phU"] + features

missing = set(required_columns) - set(data.columns)
if missing:
    raise ValueError(f"Missing CSV columns: {sorted(missing)}")

# Convert measurement columns to numeric values
for column in ["pHL", "phU"] + features:
    data[column] = pd.to_numeric(data[column], errors="coerce")

data = data.dropna(subset=required_columns).copy()
data["label"] = data["label"].astype(str).str.strip()
data = data[data["label"] != ""]

if data.empty:
    raise ValueError("The CSV has no valid crop records.")

# Standardize measurements so larger numerical scales
# do not automatically dominate the distance calculation.
scaler = StandardScaler()
scaled_data = scaler.fit_transform(data[features])


def recommend_crops(values, soil_ph, top_n=3):
    user_data = pd.DataFrame([values], columns=features)
    scaled_input = scaler.transform(user_data)

    # Compare the user's soil measurements with every record.
    distances = euclidean_distances(
        scaled_input, scaled_data
    )[0]

    results = data.copy()
    results["distance"] = distances

    # Determine whether the pH falls inside each crop's range.
    results["ph_match"] = (
        (results["pHL"] <= soil_ph) &
        (soil_ph <= results["phU"])
    )

    # Prefer crops whose pH range is suitable.
    # If none match, still show the closest alternatives.
    if results["ph_match"].any():
        results = results[results["ph_match"]].copy()
    else:
        # Penalize crops by how far the pH is outside
        # their specified acceptable range.
        results["ph_gap"] = np.maximum(
            results["pHL"] - soil_ph,
            0
        ) + np.maximum(
            soil_ph - results["phU"],
            0
        )

        ph_scale = max(
            float(data["phU"].max() - data["pHL"].min()),
            1.0
        )

        results["distance"] += results["ph_gap"] / ph_scale

    # Rank records from most to least similar.
    results = results.sort_values("distance")

    # Return each crop only once.
    results = results.drop_duplicates(subset=["label"])

    recommendations = []
    for _, row in results.head(top_n).iterrows():
        crop_label = row["label"].strip()

        # Safely fetch economic forecast for the recommended crop
        try:
            price_forecast = get_crop_price_forecast(
                crop_name=crop_label, n_months=4
            )
        except Exception:
            price_forecast = None

        crop_dict = {
            "crop": crop_label.title(),
            "similarity": round(
                100 / (1 + float(row["distance"])), 1
            ),
            "ph_range": f'{row["pHL"]} - {row["phU"]}',
            "ph_match": bool(row["ph_match"]),
            "price_forecast": price_forecast,
        }

        # Include the individual nutrient levels for the dropdown
        for name in features:
            crop_dict[name] = round(float(row[name]), 2)

        recommendations.append(crop_dict)

    return recommendations

    # return [
    #     {
    #         "crop": row["label"].title(),
    #         "similarity": round(
    #             100 / (1 + float(row["distance"])), 1
    #         ),
    #         "ph_range": f'{row["pHL"]} - {row["phU"]}',
    #         "ph_match": bool(row["ph_match"]),
    #         # the crop's levels, shown in the dropdown
    #         **{
    #             name: round(float(row[name]), 2)
    #             for name in features
    #         }
    #     }
    #     for _, row in results.head(top_n).iterrows()
    # ]


@app.route("/", methods=["GET", "POST"])
def home():
    recommendations = None
    error = None

    if request.method == "POST":
        try:
            values = [
                float(request.form[name])
                for name in features
            ]
            soil_ph = float(request.form["soil_ph"])

            if not all(np.isfinite(v) for v in values + [soil_ph]):
                raise ValueError

            if any(v < 0 for v in values):
                error = "Soil measurements cannot be negative."
            elif not 0 <= soil_ph <= 14:
                error = "Soil pH must be between 0 and 14."
            else:
                recommendations = recommend_crops(
                    values, soil_ph
                )

        except (ValueError, TypeError, KeyError):
            error = "Please enter valid numbers for every field."

    return render_template(
        "index.html",
        recommendations=recommendations,
        error=error
    )


if __name__ == "__main__":
    app.run(debug=True)