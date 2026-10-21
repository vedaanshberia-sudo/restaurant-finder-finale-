
import math
import re
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Foodie Finder | Find your next bite",
    page_icon="🍓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- DESIGN SYSTEM --------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Nunito:wght@600;700;800;900&display=swap');

:root {
    --ink: #49342e;
    --pink: #ff718b;
    --orange: #ff885d;
    --yellow: #ffe38a;
    --mint: #c9f2dc;
    --blue: #d9edff;
    --paper: #fffaf0;
}

.stApp {
    background:
        radial-gradient(ellipse at 5% 5%, #ffe1e8 0, transparent 32%),
        radial-gradient(ellipse at 95% 20%, #fff0b8 0, transparent 28%),
        #fffaf0;
    color: var(--ink);
    font-family: 'DM Sans', sans-serif;
}

.block-container {
    max-width: 1180px;
    padding-top: 1.8rem;
    padding-bottom: 4rem;
}

h1, h2, h3 {
    font-family: 'Nunito', sans-serif !important;
    color: var(--ink) !important;
    letter-spacing: -0.7px;
}

h1 { font-size: clamp(2.5rem, 6vw, 4.5rem) !important; }
h2 { font-size: 2rem !important; }

p, label, .stMarkdown {
    color: var(--ink);
}

[data-testid="stSidebar"] {
    background: #fff0e4;
    border-right: 2px solid #ffe0c7;
}

[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #b84c51 !important;
}

[data-testid="stMetric"] {
    background: white;
    border: 1px solid #ffe2d5;
    border-radius: 20px;
    padding: 16px;
    box-shadow: 0 5px 18px #6b39200b;
}

[data-testid="stMetricValue"] {
    color: #ed617a;
}

div.stButton > button,
div.stFormSubmitButton > button {
    background: linear-gradient(110deg, #ff718b, #ff9867);
    color: white;
    border: 0;
    border-radius: 16px;
    padding: 0.72rem 1rem;
    font-weight: 800;
    min-height: 48px;
    transition: transform .18s ease, box-shadow .18s ease;
    box-shadow: 0 5px 0 #e9b4a4;
}

div.stButton > button:hover,
div.stFormSubmitButton > button:hover {
    color: white;
    transform: translateY(-2px);
    box-shadow: 0 8px 0 #e9b4a4;
}

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="textarea"] > div {
    background: white;
    border-radius: 12px;
    border-color: #f3d7ca;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffffd9;
    border: 1px solid #f7ddce;
    border-radius: 22px;
    box-shadow: 0 8px 24px #8b56320b;
}

hr { border-color: #f3ddce; }

.food-hero {
    background: linear-gradient(120deg, #ffe0e8, #fff0bd 55%, #d9f6e6);
    border: 2px solid white;
    border-radius: 30px;
    padding: clamp(22px, 4vw, 44px);
    margin-bottom: 24px;
    box-shadow: 0 12px 32px #8b56320d;
}

.eyebrow {
    display: inline-block;
    background: white;
    border-radius: 999px;
    padding: 7px 13px;
    font-size: 0.82rem;
    font-weight: 800;
    color: #ba5263;
    margin-bottom: 12px;
}

.hero-copy {
    font-size: 1.08rem;
    line-height: 1.7;
    max-width: 650px;
}

.mini-note {
    background: #fff2c7;
    border-radius: 14px;
    padding: 13px 16px;
    font-size: 0.9rem;
}

.result-label {
    color: #b55361;
    font-weight: 800;
    text-transform: uppercase;
    font-size: 0.76rem;
    letter-spacing: 1px;
}

.result-name {
    font-family: 'Nunito', sans-serif;
    font-size: 1.45rem;
    font-weight: 900;
    color: #49342e;
}

.tag {
    display: inline-block;
    background: #e4f7e9;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    margin: 3px 3px 3px 0;
    font-weight: 700;
}

@media (max-width: 640px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
}
</style>
""", unsafe_allow_html=True)


# -------------------- DATA HELPERS --------------------

def norm(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def find_col(df, aliases):
    cols = {norm(c): c for c in df.columns}

    for alias in aliases:
        if norm(alias) in cols:
            return cols[norm(alias)]

    for alias in aliases:
        for normalized, original in cols.items():
            if norm(alias) in normalized:
                return original

    return None


def number(value):
    if pd.isna(value):
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group()) if match else None


def distance_km(lat1, lon1, lat2, lon2):
    radius = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.asin(min(1, math.sqrt(a)))


def read_csv(upload, path):
    try:
        if upload is not None:
            return pd.read_csv(upload)
        if Path(path).exists():
            return pd.read_csv(path)
    except Exception as exc:
        st.error(f"Could not read the CSV file: {exc}")
    return None


# -------------------- SIDEBAR --------------------

with st.sidebar:
    st.markdown("## 🍓 Foodie Finder")
    st.caption("Good food. Good mood.")

    st.markdown("---")
    st.markdown("### 📍 Your starting point")
    st.caption("Use coordinates for distance calculations.")

    user_lat = st.number_input(
        "Latitude", value=26.1445, format="%.6f"
    )
    user_lon = st.number_input(
        "Longitude", value=91.7362, format="%.6f"
    )

    st.markdown(
        '<div class="mini-note">📌 These are sample coordinates. '
        'Change them to your actual location.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### 🗂️ Bring your food data")

    restaurant_file = st.file_uploader(
        "Restaurant CSV", type=["csv"]
    )
    menu_file = st.file_uploader(
        "Menu CSV (optional)", type=["csv"]
    )

    st.caption(
        "Your files should include restaurant names, cuisine, "
        "coordinates, and prices where available."
    )


# -------------------- HERO --------------------

st.markdown("""
<div class="food-hero">
  <div class="eyebrow">✷ YOUR PERSONAL FOOD-FINDING SIDEKICK ✷</div>
  <h1>Hungry? Let's<br>fix that. 🍕</h1>
  <p class="hero-copy">
    Tell us what you're craving, how much you want to spend,
    and how far you're willing to roam. We'll help you discover
    your next delicious adventure.
  </p>
  <p><b>No boring food decisions allowed.</b> 🍓</p>
</div>
""", unsafe_allow_html=True)


# -------------------- LOAD DATA --------------------

restaurants = read_csv(
    restaurant_file, "data/restaurants.csv"
)
menu = read_csv(menu_file, "data/menu.csv")

if restaurants is None:
    st.markdown("## 🧺 First, stock the food cupboard")
    st.write(
        "Upload a restaurant CSV in the left sidebar to get started. "
        "You can download one from Kaggle."
    )

    st.markdown("""
    **Useful restaurant CSV columns**

    - `name` — restaurant name
    - `cuisines` — Italian, Indian, Chinese, etc.
    - `latitude` and `longitude` — restaurant coordinates
    - `average_cost_for_two` — estimated cost for two
    - `rating` — restaurant rating
    - `address` — restaurant address

    **Optional menu CSV columns**

    - `restaurant_name`
    - `dish_name`
    - `price`
    - `description`
    - `dietary_tags`
    - `allergens`
    """)

    st.stop()


name_col = find_col(
    restaurants, ["restaurant_name", "name", "restaurant"]
)
cuisine_col = find_col(
    restaurants, ["cuisines", "cuisine", "food_type"]
)
lat_col = find_col(restaurants, ["latitude", "lat"])
lon_col = find_col(restaurants, ["longitude", "lon", "lng"])
cost_col = find_col(
    restaurants,
    ["average_cost_for_two", "cost_for_two", "average_cost", "price", "cost"]
)
rating_col = find_col(
    restaurants, ["aggregate_rating", "rating", "rate"]
)
address_col = find_col(
    restaurants, ["address", "locality", "area", "location"]
)

if name_col is None or cuisine_col is None:
    st.error(
        "I couldn't identify the restaurant name and cuisine columns. "
        "Check the CSV column names below."
    )
    st.write(list(restaurants.columns))
    st.stop()


# -------------------- PREFERENCES --------------------

st.markdown("## 💖 Let's find your food mood")
st.caption("Choose what matters to you. Optional fields can be left blank.")

cuisine_values = sorted({
    part.strip()
    for value in restaurants[cuisine_col].dropna().astype(str)
    for part in value.split(",")
    if part.strip()
})

with st.form("food_preferences"):
    st.markdown("### 🌎 1. Pick your cuisine")

    selected_cuisines = st.multiselect(
        "What part of the food world are we visiting?",
        cuisine_values,
        placeholder="Choose Italian, Indian, Japanese...",
    )

    st.markdown("### 🍜 2. What are you in the mood for?")

    meal_style = st.selectbox(
        "Choose your craving",
        [
            "Surprise me",
            "Comfort food",
            "Protein-rich meal",
            "Healthy meal",
            "Salad or bowl",
            "Vegetarian",
            "Vegan",
            "Something spicy",
            "Dessert",
        ],
    )

    st.markdown("### 💸 3. What's the budget?")

    budget = st.number_input(
        "Maximum estimated spend per person (₹)",
        min_value=0,
        value=500,
        step=50,
    )

    st.markdown("### ⚠️ 4. Anything we should know?")

    allergies = st.multiselect(
        "Food allergies",
        [
            "Peanuts", "Tree nuts", "Milk", "Eggs",
            "Wheat / gluten", "Soy", "Fish",
            "Shellfish", "Sesame",
        ],
        placeholder="Select any relevant allergies",
    )

    st.markdown("### 🚶 5. How far will you travel?")

    max_distance = st.slider(
        "Maximum distance in kilometres",
        min_value=1,
        max_value=50,
        value=10,
    )

    submitted = st.form_submit_button(
        "🍓 Find my food match!",
        use_container_width=True,
    )


# -------------------- RESULTS --------------------

if submitted:
    df = restaurants.copy()
    df["_cuisine"] = df[cuisine_col].fillna("").astype(str)

    if selected_cuisines:
        pattern = "|".join(re.escape(x) for x in selected_cuisines)
        df = df[
            df["_cuisine"].str.contains(
                pattern, case=False, na=False
            )
        ]

    if cost_col:
        df["_raw_cost"] = df[cost_col].apply(number)

        # Interpret a "cost for two" field as a per-person estimate.
        if "two" in norm(cost_col) or "for_2" in norm(cost_col):
            df["_person_cost"] = df["_raw_cost"] / 2
        else:
            df["_person_cost"] = df["_raw_cost"]

        if budget > 0:
            df = df[
                df["_person_cost"].notna()
                & (df["_person_cost"] <= budget)
            ]

    if lat_col and lon_col:
        df["_lat"] = pd.to_numeric(df[lat_col], errors="coerce")
        df["_lon"] = pd.to_numeric(df[lon_col], errors="coerce")
        df = df.dropna(subset=["_lat", "_lon"])

        df["_distance"] = df.apply(
            lambda row: distance_km(
                user_lat, user_lon, row["_lat"], row["_lon"]
            ),
            axis=1,
        )
        df = df[df["_distance"] <= max_distance]
    else:
        df["_distance"] = float("nan")
        st.warning(
            "Your dataset has no recognized latitude/longitude columns. "
            "Results cannot be verified as nearby."
        )

    if rating_col:
        df["_rating"] = df[rating_col].apply(number)
    else:
        df["_rating"] = float("nan")

    if df.empty:
        st.markdown("## 🥹 No bites found... yet!")
        st.info(
            "Try expanding your distance, increasing your budget, "
            "or selecting fewer cuisines."
        )
    else:
        # Closest first, with rating used as a tie-breaker.
        df = df.sort_values(
            ["_distance", "_rating"],
            ascending=[True, False],
            na_position="last",
        )

        st.markdown("## 🎉 Your next food adventure")
        st.write(
            f"We found **{len(df)} matching restaurant records**. "
            "Here are your closest matches."
        )

        if meal_style != "Surprise me":
            st.info(
                f"Your craving: **{meal_style}**. "
                "This version does not yet filter dishes by meal style; "
                "menu-level matching is a future step."
            )

        for _, row in df.head(10).iterrows():
            with st.container(border=True):
                left, right = st.columns([3, 1])

                with left:
                    st.markdown(
                        '<div class="result-label">YOUR FOOD MATCH</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="result-name">🍽️ '
                        f'{row[name_col]}</div>',
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f'<span class="tag">{row[cuisine_col]}</span>',
                        unsafe_allow_html=True,
                    )

                    if address_col and pd.notna(row[address_col]):
                        st.write(f"📍 {row[address_col]}")

                    if pd.notna(row["_distance"]):
                        st.write(
                            f"🚶 About **{row['_distance']:.1f} km** away"
                        )

                    if cost_col and pd.notna(row["_person_cost"]):
                        st.write(
                            f"💰 Estimated **₹{row['_person_cost']:.0f} "
                            "per person**"
                        )

                    if pd.notna(row["_rating"]):
                        st.write(f"⭐ Dataset rating: {row['_rating']}")

                    if menu is not None:
                        dish_col = find_col(
                            menu,
                            ["dish_name", "item_name", "menu_item", "dish", "item"],
                        )
                        menu_name_col = find_col(
                            menu, ["restaurant_name", "restaurant", "name"]
                        )

                        if dish_col and menu_name_col:
                            matched = menu[
                                menu[menu_name_col]
                                .astype(str)
                                .str.strip()
                                .str.casefold()
                                == str(row[name_col]).strip().casefold()
                            ]

                            if not matched.empty:
                                st.markdown("**🍴 A dish to explore**")
                                st.write(matched.iloc[0][dish_col])
                            else:
                                st.caption(
                                    "No matching menu item was found "
                                    "for this restaurant."
                                )
                        else:
                            st.caption(
                                "Add restaurant-name and dish-name columns "
                                "to your menu CSV for dish suggestions."
                            )
                    else:
                        st.caption(
                            "Upload a menu CSV to recommend actual listed dishes."
                        )

                with right:
                    if pd.notna(row["_rating"]):
                        st.metric("⭐ Rating", f"{row['_rating']:.1f}")
                    if pd.notna(row["_distance"]):
                        st.metric("📍 Distance", f"{row['_distance']:.1f} km")

        if allergies:
            st.error(
                "⚠️ Allergy information has not been verified. "
                "This prototype cannot confirm that any restaurant or "
                "dish is safe for your allergies. Contact the restaurant "
                "to verify ingredients and cross-contact before ordering."
            )

        st.caption(
            "Prototype data may be outdated. Prices are estimates, "
            "distances are straight-line distances, and live availability "
            "has not been checked."
        )

st.markdown("---")
st.markdown(
    "<div style='text-align:center;padding:12px;'>"
    "Made with 🍓, a little curiosity, and a lot of food love."
    "</div>",
    unsafe_allow_html=True,
)
