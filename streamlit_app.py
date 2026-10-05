import json
from pathlib import Path

import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

DATA_FILE = Path(__file__).parent / "recipes.json"

# ============================================================
# ADMIN PASSWORD
# ============================================================
# CURRENTLY HARDCODED FOR LOCAL DEVELOPMENT
#
# To move this to Streamlit Secrets later:
#
# 1. Delete/replace the line below:
#       ADMIN_PASSWORD = "Admin123"
#
# 2. Replace it with:
#       ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
#
# 3. Add ADMIN_PASSWORD to .streamlit/secrets.toml locally, or
#    to the "Secrets" section of Streamlit Community Cloud.
# ============================================================
ADMIN_PASSWORD = "Admin123"


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Recipe Quick Access",
    page_icon="🍴",
    layout="wide",
)


# ============================================================
# DATA FUNCTIONS
# ============================================================

def get_recipes():
    """Load recipes from recipes.json."""
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            st.error("recipes.json does not contain a valid recipe list.")
            return []

        return data

    except FileNotFoundError:
        st.error(f"Could not find {DATA_FILE.name}.")
        return []

    except json.JSONDecodeError:
        st.error(f"{DATA_FILE.name} contains invalid JSON.")
        return []


def save_recipes(recipes):
    """Save recipes back to recipes.json."""
    try:
        with DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(recipes, file, indent=2, ensure_ascii=False)

        return True

    except OSError as error:
        st.error(f"Could not save recipes.json: {error}")
        return False


def get_recipe_time(recipe):
    """Support both 'time' and the newer 'totalTime' field."""
    value = recipe.get("totalTime", recipe.get("time", 0))

    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_ingredient_text(ingredient):
    """Convert either an ingredient string or ingredient object into text."""
    if isinstance(ingredient, str):
        return ingredient

    if isinstance(ingredient, dict):
        quantity = str(ingredient.get("quantity", "")).strip()
        unit = str(ingredient.get("unit", "")).strip()
        name = str(
            ingredient.get(
                "ingredient",
                ingredient.get("name", "")
            )
        ).strip()

        return " ".join(
            part for part in [quantity, unit, name] if part
        )

    return str(ingredient)


def get_next_recipe_id(recipes):
    """Generate the next numeric recipe ID while preserving four-digit IDs."""
    numeric_ids = []

    for recipe in recipes:
        recipe_id = str(recipe.get("id", ""))

        try:
            numeric_ids.append(int(recipe_id))
        except ValueError:
            continue

    next_id = max(numeric_ids, default=0) + 1
    return f"{next_id:04d}"


# ============================================================
# SESSION STATE
# ============================================================

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if "page" not in st.session_state:
    st.session_state.page = "recipes"

if "editing_recipe_id" not in st.session_state:
    st.session_state.editing_recipe_id = None


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
    :root {
        --bg: #f6f4ef;
        --card: #ffffff;
        --text: #202124;
        --muted: #6b6b6b;
        --accent: #b65c32;
        --accent-light: #f1dfd4;
        --border: #e4e0d9;
    }

    .stApp {
        background-color: #f6f4ef;
    }

    .recipe-card {
        background: #ffffff;
        border: 1px solid #e4e0d9;
        border-radius: 15px;
        padding: 0;
        margin-bottom: 15px;
        overflow: hidden;
    }

    .recipe-emoji {
        background: linear-gradient(135deg, #ead8ca, #f7eee8);
        min-height: 135px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 55px;
        border-radius: 15px 15px 0 0;
    }

    .recipe-card-content {
        padding: 12px;
    }

    .recipe-card-title {
        font-size: 17px;
        font-weight: 600;
        margin-bottom: 8px;
    }

    .recipe-tag {
        display: inline-block;
        font-size: 12px;
        padding: 4px 7px;
        margin: 0 4px 4px 0;
        border-radius: 999px;
        background: #f1dfd4;
        color: #713819;
    }

    .recipe-count {
        color: #6b6b6b;
        margin-bottom: 15px;
    }

    .admin-archived {
        opacity: 0.6;
    }

    .admin-visible {
        border-left: 4px solid #b65c32;
        padding-left: 10px;
    }

    div[data-testid="stForm"] {
        border: 1px solid #e4e0d9;
        border-radius: 12px;
        padding: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# RECIPE DETAIL
# ============================================================

def show_recipe(recipe):
    """Display a complete recipe."""

    st.markdown(f"# {recipe.get('emoji', '🍴')} {recipe.get('name', 'Unnamed recipe')}")

    recipe_type = recipe.get("type", "Unknown")
    difficulty = recipe.get("difficulty", "Unknown")
    recipe_time = get_recipe_time(recipe)
    portions = recipe.get("portions", "N/A")

    st.caption(
        f"{recipe_type}  •  {difficulty}  •  "
        f"{recipe_time} min  •  {portions} portions"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Ingredients")

        ingredients = recipe.get("ingredients", [])

        if ingredients:
            for ingredient in ingredients:
                st.markdown(f"- {get_ingredient_text(ingredient)}")
        else:
            st.write("No ingredients listed.")

    with col2:
        st.subheader("Method")

        method = recipe.get("method", [])

        if method:
            for number, step in enumerate(method, start=1):
                st.markdown(f"**{number}.** {step}")
        else:
            st.write("No method listed.")

    if st.button("← Back to recipes", key="back_from_recipe"):
        st.session_state.page = "recipes"
        st.rerun()


# ============================================================
# RECIPE BROWSER
# ============================================================

def show_recipe_browser(recipes):
    """Display the public recipe browser."""

    st.title("🍴 Recipe Quick Access")

    visible_recipes = [
        recipe
        for recipe in recipes
        if recipe.get("visibility", True)
    ]

    # --------------------------------------------------------
    # FILTERS
    # --------------------------------------------------------

    col1, col2, col3, col4, col5 = st.columns(
        [2, 1, 1, 1, 1]
    )

    with col1:
        search = st.text_input(
            "Search",
            placeholder="Search recipes…",
            label_visibility="collapsed",
        )

    with col2:
        meal_types = sorted(
            {
                recipe.get("type", "")
                for recipe in visible_recipes
                if recipe.get("type")
            }
        )

        selected_type = st.selectbox(
            "Meal type",
            ["All meal types"] + meal_types,
            label_visibility="collapsed",
        )

    with col3:
        difficulties = ["Easy", "Medium", "Hard"]

        selected_difficulty = st.selectbox(
            "Difficulty",
            ["All difficulties"] + difficulties,
            label_visibility="collapsed",
        )

    with col4:
        time_options = {
            "Any time": None,
            "≤ 15 min": 15,
            "≤ 30 min": 30,
            "≤ 60 min": 60,
        }

        selected_time_label = st.selectbox(
            "Time",
            list(time_options.keys()),
            label_visibility="collapsed",
        )

    with col5:
        sort_options = {
            "Name": "name",
            "Time": "time",
            "Difficulty": "difficulty",
            "Portions": "portions",
        }

        selected_sort_label = st.selectbox(
            "Sort by",
            list(sort_options.keys()),
            label_visibility="collapsed",
        )

    selected_time = time_options[selected_time_label]
    selected_sort = sort_options[selected_sort_label]

    # --------------------------------------------------------
    # FILTERING
    # --------------------------------------------------------

    result = []

    search_query = search.strip().lower()

    for recipe in visible_recipes:
        recipe_name = str(recipe.get("name", ""))
        recipe_type = str(recipe.get("type", ""))
        recipe_difficulty = str(recipe.get("difficulty", ""))
        recipe_time = get_recipe_time(recipe)

        if search_query:
            searchable_text = (
                recipe_name + " " + recipe_type
            ).lower()

            if search_query not in searchable_text:
                continue

        if (
            selected_type != "All meal types"
            and recipe_type != selected_type
        ):
            continue

        if (
            selected_difficulty != "All difficulties"
            and recipe_difficulty != selected_difficulty
        ):
            continue

        if (
            selected_time is not None
            and recipe_time > selected_time
        ):
            continue

        result.append(recipe)

    # --------------------------------------------------------
    # SORTING
    # --------------------------------------------------------

    difficulty_rank = {
        "Easy": 1,
        "Medium": 2,
        "Hard": 3,
    }

    if selected_sort == "name":
        result.sort(
            key=lambda recipe: str(
                recipe.get("name", "")
            ).lower()
        )

    elif selected_sort == "time":
        result.sort(key=get_recipe_time)

    elif selected_sort == "portions":
        result.sort(
            key=lambda recipe: int(
                recipe.get("portions", 0)
            )
            if str(recipe.get("portions", "")).isdigit()
            else 0
        )

    elif selected_sort == "difficulty":
        result.sort(
            key=lambda recipe: difficulty_rank.get(
                recipe.get("difficulty"),
                99,
            )
        )

    # --------------------------------------------------------
    # RESULT COUNT
    # --------------------------------------------------------

    recipe_word = "recipe" if len(result) == 1 else "recipes"

    st.markdown(
        f'<p class="recipe-count">{len(result)} {recipe_word}</p>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # RECIPE GRID
    # --------------------------------------------------------

    if not result:
        st.info("No recipes match the selected filters.")
        return

    # Five columns on large screens gives a similar feel to the
    # original CSS grid while remaining usable on smaller screens.
    columns = st.columns(5)

    for index, recipe in enumerate(result):
        column = columns[index % 5]

        with column:
            emoji = recipe.get("emoji", "🍴")
            name = recipe.get("name", "Unnamed recipe")
            recipe_type = recipe.get("type", "")
            difficulty = recipe.get("difficulty", "")
            recipe_time = get_recipe_time(recipe)
            portions = recipe.get("portions", "")

            st.markdown(
                f"""
                <div class="recipe-card">
                    <div class="recipe-emoji">{emoji}</div>
                    <div class="recipe-card-content">
                        <div class="recipe-card-title">{name}</div>
                        <span class="recipe-tag">{recipe_type}</span>
                        <span class="recipe-tag">{difficulty}</span>
                        <span class="recipe-tag">⏱ {recipe_time} min</span>
                        <span class="recipe-tag">👥 {portions}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "View recipe",
                key=f"view_{recipe.get('id')}",
                use_container_width=True,
            ):
                st.session_state.selected_recipe_id = recipe.get("id")
                st.session_state.page = "recipe"
                st.rerun()


# ============================================================
# ADMIN LOGIN
# ============================================================

def show_admin_login():
    """Display the admin login page."""

    st.title("🔐 Admin Login")

    st.write("Enter the administrator password to manage recipes.")

    with st.form("login_form"):
        password = st.text_input(
            "Password",
            type="password",
        )

        submitted = st.form_submit_button(
            "Login",
            use_container_width=True,
        )

        if submitted:
            if password == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.session_state.page = "admin"
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Incorrect password.")


# ============================================================
# ADMIN RECIPE EDITOR
# ============================================================

def show_recipe_editor(recipes, recipe=None):
    """Display the add/edit recipe form."""

    editing = recipe is not None

    if editing:
        st.subheader(f"Edit: {recipe.get('name', 'Recipe')}")
    else:
        st.subheader("Add New Recipe")

    current_ingredients = (
        recipe.get("ingredients", [])
        if editing
        else []
    )

    current_method = (
        recipe.get("method", [])
        if editing
        else []
    )

    # Convert object-based ingredients to text for the editor.
    ingredient_text = "\n".join(
        get_ingredient_text(item)
        for item in current_ingredients
    )

    method_text = "\n".join(
        str(step)
        for step in current_method
    )

    with st.form(
        "recipe_editor_form",
        clear_on_submit=False,
    ):
        name = st.text_input(
            "Recipe name",
            value=recipe.get("name", "") if editing else "",
        )

        col1, col2 = st.columns(2)

        with col1:
            meal_types = [
                "Starter",
                "Main",
                "Side",
                "Dessert",
                "Breakfast",
                "Drink",
                "Snack",
            ]

            current_type = (
                recipe.get("type", "Main")
                if editing
                else "Main"
            )

            if current_type not in meal_types:
                meal_types.append(current_type)

            recipe_type = st.selectbox(
                "Meal type",
                meal_types,
                index=meal_types.index(current_type),
            )

        with col2:
            difficulties = ["Easy", "Medium", "Hard"]

            current_difficulty = (
                recipe.get("difficulty", "Easy")
                if editing
                else "Easy"
            )

            if current_difficulty not in difficulties:
                difficulties.append(current_difficulty)

            difficulty = st.selectbox(
                "Difficulty",
                difficulties,
                index=difficulties.index(current_difficulty),
            )

        col1, col2, col3 = st.columns(3)

        with col1:
            time = st.number_input(
                "Cooking time (minutes)",
                min_value=0,
                step=1,
                value=get_recipe_time(recipe) if editing else 0,
            )

        with col2:
            portions_default = (
                recipe.get("portions", 1)
                if editing
                else 1
            )

            try:
                portions_default = int(portions_default)
            except (TypeError, ValueError):
                portions_default = 1

            portions = st.number_input(
                "Portions",
                min_value=1,
                step=1,
                value=portions_default,
            )

        with col3:
            emoji = st.text_input(
                "Emoji",
                value=recipe.get("emoji", "🍴") if editing else "🍴",
                max_chars=4,
            )

        ingredients = st.text_area(
            "Ingredients — one per line",
            value=ingredient_text,
            height=180,
        )

        method = st.text_area(
            "Method — one step per line",
            value=method_text,
            height=220,
        )

        if editing:
            visibility = st.checkbox(
                "Visible on recipe page",
                value=recipe.get("visibility", True),
            )
        else:
            visibility = True

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button(
                "Save recipe",
                type="primary",
                use_container_width=True,
            )

        with col2:
            cancelled = st.form_submit_button(
                "Cancel",
                use_container_width=True,
            )

        if cancelled:
            st.session_state.editing_recipe_id = None
            st.rerun()

        if submitted:
            cleaned_name = name.strip()

            if not cleaned_name:
                st.error("Please enter a recipe name.")
                return

            ingredient_list = [
                line.strip()
                for line in ingredients.splitlines()
                if line.strip()
            ]

            method_list = [
                line.strip()
                for line in method.splitlines()
                if line.strip()
            ]

            if editing:
                recipe["name"] = cleaned_name
                recipe["type"] = recipe_type
                recipe["difficulty"] = difficulty
                recipe["time"] = int(time)
                recipe["portions"] = int(portions)
                recipe["emoji"] = emoji.strip() or "🍴"
                recipe["ingredients"] = ingredient_list
                recipe["method"] = method_list
                recipe["visibility"] = visibility

                message = "Recipe updated successfully."

            else:
                new_recipe = {
                    "id": get_next_recipe_id(recipes),
                    "visibility": True,
                    "name": cleaned_name,
                    "type": recipe_type,
                    "difficulty": difficulty,
                    "time": int(time),
                    "portions": int(portions),
                    "emoji": emoji.strip() or "🍴",
                    "ingredients": ingredient_list,
                    "method": method_list,
                }

                recipes.append(new_recipe)
                message = "Recipe added successfully."

            if save_recipes(recipes):
                st.session_state.editing_recipe_id = None
                st.success(message)
                st.rerun()


# ============================================================
# ADMIN DASHBOARD
# ============================================================

def show_admin(recipes):
    """Display the admin dashboard."""

    st.title("⚙️ Recipe Admin")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            "← Recipe browser",
            use_container_width=True,
        ):
            st.session_state.page = "recipes"
            st.rerun()

    with col2:
        if st.button(
            "➕ Add recipe",
            use_container_width=True,
        ):
            st.session_state.editing_recipe_id = "NEW"
            st.rerun()

    with col3:
        if st.button(
            "Logout",
            use_container_width=True,
        ):
            st.session_state.admin_logged_in = False
            st.session_state.page = "recipes"
            st.rerun()

    st.divider()

    # --------------------------------------------------------
    # ADD / EDIT FORM
    # --------------------------------------------------------

    if st.session_state.editing_recipe_id == "NEW":
        show_recipe_editor(recipes)
        st.divider()

    elif st.session_state.editing_recipe_id is not None:
        editing_recipe = next(
            (
                recipe
                for recipe in recipes
                if recipe.get("id")
                == st.session_state.editing_recipe_id
            ),
            None,
        )

        if editing_recipe:
            show_recipe_editor(
                recipes,
                editing_recipe,
            )
            st.divider()
        else:
            st.session_state.editing_recipe_id = None

    # --------------------------------------------------------
    # RECIPE MANAGEMENT
    # --------------------------------------------------------

    st.subheader("Manage Recipes")

    visible_count = sum(
        recipe.get("visibility", True)
        for recipe in recipes
    )

    archived_count = len(recipes) - visible_count

    st.caption(
        f"{len(recipes)} total • "
        f"{visible_count} visible • "
        f"{archived_count} archived"
    )

    # Visible recipes first, followed by archived recipes.
    sorted_recipes = sorted(
        recipes,
        key=lambda recipe: (
            not recipe.get("visibility", True),
            str(recipe.get("name", "")).lower(),
        ),
    )

    for recipe in sorted_recipes:
        is_visible = recipe.get("visibility", True)
        recipe_id = recipe.get("id")
        name = recipe.get("name", "Unnamed recipe")

        with st.container(border=True):
            col1, col2, col3, col4 = st.columns(
                [3, 2, 1, 1]
            )

            with col1:
                status = "🟢 Visible" if is_visible else "⚪ Archived"
                st.markdown(f"**{name}**")
                st.caption(
                    f"{status} • ID: {recipe_id}"
                )

            with col2:
                st.caption(
                    f"{recipe.get('type', '')} • "
                    f"{recipe.get('difficulty', '')} • "
                    f"{get_recipe_time(recipe)} min • "
                    f"{recipe.get('portions', '')} portions"
                )

            with col3:
                if st.button(
                    "Edit",
                    key=f"edit_{recipe_id}",
                    use_container_width=True,
                ):
                    st.session_state.editing_recipe_id = recipe_id
                    st.rerun()

            with col4:
                button_text = (
                    "Archive"
                    if is_visible
                    else "Restore"
                )

                if st.button(
                    button_text,
                    key=f"toggle_{recipe_id}",
                    use_container_width=True,
                ):
                    recipe["visibility"] = not is_visible

                    if save_recipes(recipes):
                        st.rerun()


# ============================================================
# MAIN APPLICATION
# ============================================================

recipes = get_recipes()


# Sidebar navigation is deliberately simple. The public recipe
# browser remains accessible without logging in.
with st.sidebar:
    st.header("🍴 Recipe Book")

    if st.button(
        "📖 Recipes",
        use_container_width=True,
    ):
        st.session_state.page = "recipes"
        st.session_state.editing_recipe_id = None
        st.rerun()

    if st.session_state.admin_logged_in:
        if st.button(
            "⚙️ Admin",
            use_container_width=True,
        ):
            st.session_state.page = "admin"
            st.session_state.editing_recipe_id = None
            st.rerun()

        st.success("Admin logged in")

    else:
        if st.button(
            "🔐 Admin Login",
            use_container_width=True,
        ):
            st.session_state.page = "login"
            st.rerun()


# ------------------------------------------------------------
# PAGE ROUTING
# ------------------------------------------------------------

if st.session_state.page == "recipe":
    selected_id = st.session_state.get(
        "selected_recipe_id"
    )

    selected_recipe = next(
        (
            recipe
            for recipe in recipes
            if recipe.get("id") == selected_id
        ),
        None,
    )

    if selected_recipe and selected_recipe.get(
        "visibility",
        True,
    ):
        show_recipe(selected_recipe)
    else:
        st.warning("That recipe is no longer available.")
        if st.button("← Back to recipes"):
            st.session_state.page = "recipes"
            st.rerun()

elif st.session_state.page == "login":
    if st.session_state.admin_logged_in:
        st.session_state.page = "admin"
        st.rerun()

    show_admin_login()

elif st.session_state.page == "admin":
    if not st.session_state.admin_logged_in:
        st.session_state.page = "login"
        st.rerun()

    show_admin(recipes)

else:
    show_recipe_browser(recipes)
