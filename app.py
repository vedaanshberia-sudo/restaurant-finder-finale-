
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Foodie Finder",
    page_icon="🍜",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #fff8e9, #fff0f4, #eaf8ff);
}
h1 { color: #ef5b45; }
div.stButton > button {
    background: #ff715b;
    color: white;
    border-radius: 14px;
    border: none;
    font-weight: 700;
}
[data-testid="stMetric"] {
    background: white;
    border-radius: 15px;
    padding: 14px;
}
</style>
""", unsafe_allow_html=True)

st.title("🍜 Foodie Finder")
st.subheader("Your cravings. Your budget. Your next favorite place.")
st.write("Find restaurants that match your taste, wherever you are.")

# ---------- DATA HELPERS ----------

def normalize(text):
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")

def find_col(df, possible_names):
    columns = {normalize(c): c for c in df.columns}
    for name in possible_names:
        if normalize(name) in columns:
            return columns[normalize(name)]
    for name in possible_names:
        for normalized, original in columns.items():
            if normalize(name) in normalized:
                return original
    return None

def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2)**2 + (
        math.cos(p1) * math.cos(p2) * math.sin(dl / 2)**2
    )
    return 2 * radius * math.asin(min(1, math.sqrt(a)))

def load_csv(upload, default_path):
    if upload is not None:
        return pd.read_csv(upload)
    if Path(default_path).exists():
        return pd.read_csv(default_path)
    return None

# ---------- DATA INPUT ----------

with st.sidebar:
    st.header("📍 Your location")
    st.caption("Enter coordinates for distance-based results.")
    user_lat = st.number_input(
        "Latitude", value=26.1445, format="%.6f"
    )
    user_lon = st.number_input(
        "Longitude", value=91.7362, format="%.6f"
    )
    st.caption(
        "The initial coordinates are sample coordinates. "
        "Replace them with your actual location."
    )

    st.divider()
    st.header("📂 Restaurant data")
    restaurant_upload = st.file_uploader(
        "Upload restaurant CSV", type=["csv"]
    )
    menu_upload = st.file_uploader(
        "Optional: upload menu CSV", type=["csv"]
    )

restaurants = load_csv(
    restaurant_upload, "data/restaurants.csv"
)
menu = load_csv(menu_upload, "data/menu.csv")

if restaurants is None:
    st.info(
        "Upload a Kaggle restaurant CSV in the sidebar, "
        "or add it to data/restaurants.csv in your repository."
    )
    st.write("Your CSV should ideally contain:")
    st.code(
        "name, cuisines, latitude, longitude, "
        "average_cost_for_two, rating, address"
    )
    st.stop()

# Identify common column names in different Kaggle datasets.
name_col = find_col(restaurants, [
    "name", "restaurant_name", "restaurant"
])
cuisine_col = find_col(restaurants, [
    "cuisines", "cuisine", "food_type"
])
lat_col = find_col(restaurants, [
    "latitude", "lat"
])
lon_col = find_col(restaurants, [
    "longitude", "lon", "lng"
])
cost_col = find_col(restaurants, [
    "average_cost_for_two", "cost_for_two",
    "average_cost", "price", "cost"
])
rating_col = find_col(restaurants, [
    "aggregate_rating", "rating", "rate"
])
address_col = find_col(restaurants, [
    "address", "location", "locality", "area"
])

if name_col is None or cuisine_col is None:
    st.error(
        "Could not identify restaurant name and cuisine columns. "
        "Rename them to 'name' and 'cuisines', then upload again."
    )
    st.write("Columns found:", list(restaurants.columns))
    st.stop()

# ---------- USER PREFERENCES ----------

st.header("✨ Build your food mood")

c1, c2 = st.columns(2)

with c1:
    cuisines = sorted({
        item.strip()
        for value in restaurants[cuisine_col].dropna().astype(str)
        for item in value.split(",")
        if item.strip()
    })

    chosen_cuisines = st.multiselect(
        "🌍 Which cuisine do you want?",
        cuisines,
        help="Leave blank to consider all cuisines."
    )

    meal_style = st.selectbox(
        "🍽️ What are you craving?",
        [
            "Anything",
            "Comfort food",
            "Protein-rich meal",
            "Healthy meal",
            "Salad or bowl",
            "Vegetarian",
            "Vegan",
            "Something spicy",
            "Dessert"
        ]
    )

with c2:
    budget = st.number_input(
        "💸 Maximum budget per person",
        min_value=0,
        value=500,
        step=50,
        help="Enter the maximum amount in your local currency."
    )

    allergy_options = [
        "Peanuts", "Tree nuts", "Milk", "Eggs",
        "Wheat / gluten", "Soy", "Fish", "Shellfish",
        "Sesame"
    ]
    allergies = st.multiselect(
        "⚠️ Allergies to check",
        allergy_options
    )

    max_distance = st.slider(
        "🚶 Maximum distance (km)",
        min_value=1, max_value=50, value=10
    )

search = st.button("🔎 Find my food match", use_container_width=True)

# ---------- RECOMMENDATION ENGINE ----------

if search:
    df = restaurants.copy()

    df["_cuisine"] = df[cuisine_col].fillna("").astype(str)

    if chosen_cuisines:
        pattern = "|".join(
            re.escape(c) for c in chosen_cuisines
        )
        df = df[
            df["_cuisine"].str.contains(
                pattern, case=False, na=False, regex=True
            )
        ]

    # A numeric cost field is required for strict budget filtering.
    if cost_col:
        df["_cost"] = pd.to_numeric(
            df[cost_col].astype(str).str.replace(
                r"[^0-9.]", "", regex=True
            ),
            errors="coerce"
        )
        # "Cost for two" is divided by two for a per-person estimate.
        cost_label = normalize(cost_col)
        if "two" in cost_label or "for_2" in cost_label:
            df["_person_cost"] = df["_cost"] / 2
        else:
            df["_person_cost"] = df["_cost"]

        if budget > 0:
            df = df[
                df["_person_cost"].notna()
                & (df["_person_cost"] <= budget)
            ]
    else:
        st.warning(
            "No recognizable price column. Budget cannot be verified."
        )

    if lat_col and lon_col:
        df["_lat"] = pd.to_numeric(df[lat_col], errors="coerce")
        df["_lon"] = pd.to_numeric(df[lon_col], errors="coerce")
        df = df.dropna(subset=["_lat", "_lon"])

        df["_distance"] = df.apply(
            lambda r: haversine_km(
                user_lat, user_lon, r["_lat"], r["_lon"]
            ), axis=1
        )
        df = df[df["_distance"] <= max_distance]
    else:
        st.warning(
            "No latitude/longitude columns found. "
            "Distance cannot be calculated accurately."
        )
        df["_distance"] = np.nan

    if rating_col:
        df["_rating"] = pd.to_numeric(
            df[rating_col], errors="coerce"
        ).fillna(0)
    else:
        df["_rating"] = 0

    # Only use menu information if a separate menu CSV is supplied.
    dish_col = None
    if menu is not None:
        dish_col = find_col(menu, [
            "dish_name", "item_name", "menu_item", "dish", "item"
        ])

    if df.empty:
        st.warning(
            "No matching restaurants were found. "
            "Try a larger distance or budget, or fewer filters."
        )
    else:
        df = df.sort_values(
            ["_distance", "_rating"],
            ascending=[True, False],
            na_position="last"
        )

        st.success(f"Found {len(df)} matching restaurants!")
        st.caption(
            "Ranked by distance first, then rating. "
            "Only dataset records are shown; availability is not live."
        )

        for _, row in df.head(10).iterrows():
            restaurant_name = str(row[name_col])
            cuisine_text = str(row[cuisine_col])

            with st.container(border=True):
                left, right = st.columns([3, 1])

                with left:
                    st.subheader(f"🍴 {restaurant_name}")
                    st.write(f"**Cuisine:** {cuisine_text}")

                    if address_col and pd.notna(row[address_col]):
                        st.write(f"📍 {row[address_col]}")

                    if not pd.isna(row["_distance"]):
                        st.write(
                            f"📏 Approx. {row['_distance']:.1f} km away"
                        )

                    if cost_col and pd.notna(row["_person_cost"]):
                        st.write(
                            f"💰 Approx. {row['_person_cost']:.0f} "
                            "per person (dataset estimate)"
                        )

                    if rating_col:
                        st.write(f"⭐ Rating: {row['_rating']}")

                    # Match dishes by restaurant name if the menu
                    # dataset contains a restaurant-name column.
                    if menu is not None and dish_col:
                        menu_rest_col = find_col(menu, [
                            "restaurant_name", "restaurant", "name"
                        ])
                        if menu_rest_col:
                            items = menu[
                                menu[menu_rest_col].astype(str).str.casefold()
                                == restaurant_name.casefold()
                            ]
                            if not items.empty:
                                st.write(
                                    "**Menu item to explore:** "
                                    + str(items.iloc[0][dish_col])
                                )
                            else:
                                st.write(
                                    "**Dish suggestion:** Menu match "
                                    "not available in this dataset."
                                )
                        else:
                            st.write(
                                "**Dish suggestion:** Menu CSV needs "
                                "a restaurant-name column to match dishes."
                            )
                    else:
                        st.write(
                            "**Dish suggestion:** Add a menu CSV to "
                            "recommend a real listed dish."
                        )

                with right:
                    st.metric("Rating", f"{row['_rating']:.1f}")
                    if not pd.isna(row["_distance"]):
                        st.metric(
                            "Distance", f"{row['_distance']:.1f} km"
                        )

        if allergies:
            st.warning(
                "Allergy safety has NOT been verified by this starter app. "
                "It does not have reliable ingredient or cross-contact "
                "data, so confirm directly with the restaurant before "
                "ordering. Do not treat these results as allergy-safe."
            )

        st.caption(
            "Prototype only: dataset prices, ratings, hours and locations "
            "may be old. Confirm details with the restaurant."
        )
