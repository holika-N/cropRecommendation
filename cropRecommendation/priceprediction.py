import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

CSV_PATH = "USDA No Null Crop Prices 2022_2026_Monthly_ILLINOIS.csv"


def get_crop_price_forecast(
    crop_name: str, n_months: int = 4, target_date_str: str = None
):
    """Unified API function called by app.py"""
    
    df = pd.read_csv(CSV_PATH)

    # 1. SPECIAL CASE: Pumpkins (Annual + Seasonal Multiplier)
    if crop_name == "pumpkin":
        # Target year/month default to October 2027 if specified or next harvest
        target_year = 2027
        target_month = 10  # Peak October harvest

        pumpkins = df[
            (df["Commodity"] == "PUMPKINS")
            & (df["Data Item"].str.contains("FRESH MARKET"))
        ].sort_values("Year")
        x = pumpkins["Year"].values
        y = pumpkins["Value"].values

        slope, intercept = np.polyfit(x, y, 1)
        base_annual_2027 = slope * target_year + intercept
        october_price = round(base_annual_2027 * 1.15, 2)  # 1.15x peak multiplier

        return {
            "commodity": "PUMPKINS",
            "type": "annual_seasonal",
            "forecast_type": "Peak Harvest Target",
            "target_period": f"October {target_year}",
            "forecast_price": october_price,
            "unit": "$/cwt",
            "monthly_breakdown": [
                {
                    "month": f"October {target_year}",
                    "price": october_price,
                    "unit": "$/cwt",
                }
            ],
        }

    # 2. SPECIAL CASE: Potatoes
    elif crop_name == "potato":
        min_price = 2.50  # Hardcoded minimum price total

        return {
            "commodity": "POTATOES",
            "type": "minimum_price",
            "forecast_type": "Minimum Price Guarantee",
            "target_period": f"Next {n_months} Months",
            "forecast_price": min_price,
            "unit": "$/lbs",
            "monthly_breakdown": [
                {
                    "month": f"Month {i+1}",
                    "price": min_price,
                    "unit": "$/cwt",
                }
                for i in range(n_months)
            ],
        }

    elif crop_name == "cauliflower":
        min_price = 4.00  # Hardcoded minimum price total
        return {
            "commodity": "CAULIFLOWER",
            "type": "minimum_price",
            "forecast_type": "Minimum Price Guarantee",
            "target_period": f"Next {n_months} Months",
            "forecast_price": min_price,
            "unit": "$/lbs",
            "monthly_breakdown": [
                {
                    "month": f"Month {i+1}",
                    "price": min_price,
                    "unit": "$/cwt",
                }
                for i in range(n_months)
            ],
        }

    # 3. STANDARD CASE: Corn, Soybeans, Wheat (Monthly SARIMA)
    else:
        if crop_name == "corn":
            crop_name = "CORN"
        elif crop_name == "winter wheat":
            crop_name = "WHEAT"
        elif crop_name == "soybean":
            crop_name = "SOYBEANS"
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

        crop_series = (
            monthly_df[monthly_df["Commodity"] == crop_name]
            .drop_duplicates(subset=["Date"])
            .set_index("Date")["Value"]
            .asfreq("MS")
        )

        model = SARIMAX(
            crop_series,
            order=(1, 1, 1),
            seasonal_order=(1, 0, 0, 12),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        results = model.fit(disp=False)
        forecast = results.get_forecast(steps=n_months)

        monthly_list = []
        for dt, val in zip(
            forecast.predicted_mean.index, forecast.predicted_mean
        ):
            monthly_list.append(
                {
                    "month": dt.strftime("%B %Y"),
                    "price": round(val, 2),
                    "unit": "$/bu",
                }
            )

        return {
            "commodity": crop_name,
            "type": "sarima_monthly",
            "forecast_type": f"{n_months}-Month Horizon",
            "target_period": f"{monthly_list[0]['month']} - {monthly_list[-1]['month']}",
            "forecast_price": monthly_list[-1]["price"],
            "unit": "$/bu",
            "monthly_breakdown": monthly_list,
        }