import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX


def predict_crop_prices(
    csv_file: str, commodity: str, n_months: int = 4
) -> pd.DataFrame:
    """Predicts future prices for a specific crop for 'n_months' ahead.

    Returns a pandas DataFrame with predicted values and confidence intervals.
    """

    df = pd.read_csv(csv_file)

    # Clean data & set up monthly datetime index
    monthly_df = df[df["Period"] != "MARKETING YEAR"].copy()
    month_map = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }
    monthly_df["Month_Num"] = monthly_df["Period"].map(month_map)
    monthly_df["Date"] = pd.to_datetime(
        monthly_df["Year"].astype(str)
        + "-"
        + monthly_df["Month_Num"].astype(str)
        + "-01"
    )

    # Filter for target commodity
    crop_series = (
        monthly_df[monthly_df["Commodity"] == commodity.upper()]
        .drop_duplicates(subset=["Date"])
        .set_index("Date")["Value"]
        .asfreq("MS")
    )

    # Fit Seasonal ARIMA Model
    model = SARIMAX(
        crop_series,
        order=(1, 1, 1),
        seasonal_order=(1, 0, 0, 12),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    results = model.fit(disp=False)

    #Predict n_months steps ahead
    predict = results.get_forecast(steps=n_months)
    pred_means = predict.predicted_mean
    conf_ints = predict.conf_int()

    # Build structured output table
    results_list = []
    for date, mean_val, ci in zip(
        pred_means.index, pred_means, conf_ints.values
    ):
        results_list.append(
            {
                "Commodity": commodity.upper(),
                "Target Month": date.strftime("%B %Y"),
                "Predicted Price ($/bu)": round(mean_val, 2),
                "Lower 95% CI": round(ci[0], 2),
                "Upper 95% CI": round(ci[1], 2),
            }
        )

    return pd.DataFrame(results_list)

import numpy as np
import pandas as pd


#pumpkins only right now.
def predict_annual_crop_prices(
    csv_file: str, commodity: str, target_year: int, target_month: int
) -> float:
    """Estimates a monthly price for annual-only crops like Pumpkins by combining linear trend projection with harvest seasonality weighting."""
    # Filter for target commodity marketing year data
    df = pd.read_csv(csv_file)
    crop_df = df[
        (df["Commodity"] == commodity.upper())
        & (df["Period"] == "MARKETING YEAR")
    ].copy()

    # Fit linear regression over historical years
    x = crop_df["Year"].values
    y = crop_df["Value"].values
    slope, intercept = np.polyfit(x, y, 1)

    # Base projected price for the target year
    projected_annual_price = slope * target_year + intercept

    # Seasonal weighting factors (Pumpkin demand peaks Sept-Nov)
    # Month 9 (Sep): 1.05x, Month 10 (Oct): 1.15x, Month 11 (Nov): 0.90x, Off-season: 0.80x
    seasonal_weights = {
        9: 1.05,
        10: 1.15,
        11: 0.90,
    }
    weight = seasonal_weights.get(target_month, 0.80)

    return round(projected_annual_price * weight, 2)

# --- Example Usage ---
if __name__ == "__main__":
    csv_filename = "USDA No Null Crop Prices 2022_2026_Monthly_ILLINOIS.csv"

    # Predict next 4 months for Corn, Soybeans, and Wheat
    num = 8
    for crop in ["CORN", "SOYBEANS", "WHEAT"]:
        prediction_df = predict_crop_prices(
            csv_file=csv_filename, commodity=crop, n_months=num
        )
        print(f"\n=== {crop} {num}-MONTH Prediction ===")
        print(prediction_df.to_string(index=False))


    prediction = predict_annual_crop_prices(csv_filename, "Pumpkins", 2029, "oct")
    print(f"\n=== Pumpkin 2029 October price prediction ($ / CWT) ===")
    print(prediction)