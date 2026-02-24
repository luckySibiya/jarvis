"""Extended knowledge module — movies, sports, recipes, jokes, science, and more.

Expands Jarvis's knowledge capabilities with additional free, keyless data sources.
"""

import re
import requests
from datetime import datetime, timedelta

from core.command_router import register
from config import USER_AGENT, REQUEST_TIMEOUT
from utils.logger import get_logger

logger = get_logger(__name__)

_HEADERS = {"User-Agent": USER_AGENT}


def _truncate(text: str, limit: int = 400) -> str:
    """Truncate text to a sentence boundary within the character limit."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(".", 1)
    if len(cut) > 1 and len(cut[0]) > limit // 3:
        return cut[0] + "."
    return text[:limit].rsplit(" ", 1)[0] + "..."


# ---------------------------------------------------------------------------
# Movies & TV
# ---------------------------------------------------------------------------

@register("knowledge", "movie")
def movie_info(title: str) -> str:
    """Look up movie info using DuckDuckGo instant answers."""
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={
                "q": f"{title} movie",
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            },
            headers=_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()

        abstract = data.get("AbstractText", "")
        heading = data.get("Heading", title)
        source = data.get("AbstractSource", "")

        if abstract:
            abstract = _truncate(abstract)
            result = f"{heading}: {abstract}"
            if source:
                result += f" (Source: {source})"
            return result

        # Fallback to Related Topics
        related = data.get("RelatedTopics", [])
        if related and isinstance(related[0], dict):
            text = related[0].get("Text", "")
            if text:
                return f"Here's what I found about '{title}': {_truncate(text)}"

        return (
            f"I couldn't find detailed movie info for '{title}', sir. "
            "Try asking me to search the web for more details."
        )
    except Exception as e:
        logger.error(f"Movie info error: {e}")
        return f"Sorry, I couldn't look up the movie '{title}': {e}"


@register("knowledge", "tv_show")
def tv_show_info(title: str) -> str:
    """Look up TV show info using DuckDuckGo instant answers."""
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={
                "q": f"{title} TV series",
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            },
            headers=_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()

        abstract = data.get("AbstractText", "")
        heading = data.get("Heading", title)
        source = data.get("AbstractSource", "")

        if abstract:
            abstract = _truncate(abstract)
            result = f"{heading}: {abstract}"
            if source:
                result += f" (Source: {source})"
            return result

        related = data.get("RelatedTopics", [])
        if related and isinstance(related[0], dict):
            text = related[0].get("Text", "")
            if text:
                return f"Here's what I found about '{title}': {_truncate(text)}"

        return (
            f"I couldn't find detailed TV show info for '{title}', sir. "
            "Try asking me to search the web for more details."
        )
    except Exception as e:
        logger.error(f"TV show info error: {e}")
        return f"Sorry, I couldn't look up the TV show '{title}': {e}"


# ---------------------------------------------------------------------------
# Sports
# ---------------------------------------------------------------------------

_SPORT_LEAGUES = {
    "soccer": ("soccer", "eng.1"),        # English Premier League
    "football": ("football", "nfl"),       # NFL
    "basketball": ("basketball", "nba"),   # NBA
    "baseball": ("baseball", "mlb"),       # MLB
    "hockey": ("hockey", "nhl"),           # NHL
    "cricket": ("cricket", "icc"),         # ICC
}


@register("knowledge", "sports")
def sports_scores(sport: str = "", team: str = "") -> str:
    """Get latest sports scores from ESPN's free API."""
    sport = sport.lower().strip() if sport else ""
    team = team.lower().strip() if team else ""

    # Default to football if no sport specified
    if not sport:
        sport = "football"

    league_info = _SPORT_LEAGUES.get(sport)
    if not league_info:
        available = ", ".join(sorted(_SPORT_LEAGUES.keys()))
        return (
            f"I don't have scores for '{sport}' yet, sir. "
            f"I can check: {available}."
        )

    sport_path, league = league_info

    try:
        url = (
            f"https://site.api.espn.com/apis/site/v2/sports/"
            f"{sport_path}/{league}/scoreboard"
        )
        resp = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
        data = resp.json()

        events = data.get("events", [])
        if not events:
            return f"No recent {sport} scores available right now, sir."

        results = []
        for event in events[:5]:
            name = event.get("name", "Unknown")
            status = (
                event.get("status", {})
                .get("type", {})
                .get("shortDetail", "")
            )
            competitions = event.get("competitions", [])
            if competitions:
                competitors = competitions[0].get("competitors", [])
                scores = []
                for c in competitors:
                    team_name = c.get("team", {}).get("abbreviation", "???")
                    score = c.get("score", "?")
                    scores.append(f"{team_name} {score}")
                score_line = " vs ".join(scores)
            else:
                score_line = name

            # Filter by team name if specified
            if team and team not in name.lower():
                continue

            line = f"{score_line}"
            if status:
                line += f" ({status})"
            results.append(line)

        if not results:
            if team:
                return f"No recent scores found for '{team}' in {sport}, sir."
            return f"No recent {sport} scores available right now, sir."

        header = f"Latest {sport} scores: "
        body = "; ".join(results)
        return _truncate(header + body)

    except Exception as e:
        logger.error(f"Sports scores error: {e}")
        return f"Sorry, I couldn't fetch {sport} scores right now: {e}"


# ---------------------------------------------------------------------------
# Recipes
# ---------------------------------------------------------------------------

@register("knowledge", "recipe")
def recipe_search(dish: str) -> str:
    """Search for a recipe using TheMealDB free API."""
    try:
        resp = requests.get(
            "https://www.themealdb.com/api/json/v1/1/search.php",
            params={"s": dish},
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        meals = data.get("meals")

        if not meals:
            return f"I couldn't find a recipe for '{dish}', sir."

        meal = meals[0]
        name = meal.get("strMeal", dish)
        category = meal.get("strCategory", "Unknown")
        area = meal.get("strArea", "")
        instructions = meal.get("strInstructions", "No instructions available.")

        # Collect ingredients
        ingredients = []
        for i in range(1, 21):
            ingredient = meal.get(f"strIngredient{i}", "")
            measure = meal.get(f"strMeasure{i}", "")
            if ingredient and ingredient.strip():
                ingredients.append(
                    f"{measure.strip()} {ingredient.strip()}".strip()
                )

        ingredient_list = ", ".join(ingredients[:8])
        if len(ingredients) > 8:
            ingredient_list += f", and {len(ingredients) - 8} more"

        # Truncate instructions for speech
        short_instructions = _truncate(instructions, 200)

        origin = f" ({area})" if area else ""
        result = (
            f"Recipe for {name}{origin}, category: {category}. "
            f"Key ingredients: {ingredient_list}. "
            f"Instructions: {short_instructions}"
        )
        return _truncate(result)

    except Exception as e:
        logger.error(f"Recipe search error: {e}")
        return f"Sorry, I couldn't find a recipe for '{dish}': {e}"


# ---------------------------------------------------------------------------
# Jokes & Fun
# ---------------------------------------------------------------------------

@register("knowledge", "joke")
def random_joke() -> str:
    """Get a random joke from the Official Joke API."""
    try:
        resp = requests.get(
            "https://official-joke-api.appspot.com/random_joke",
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        setup = data.get("setup", "")
        punchline = data.get("punchline", "")
        if setup and punchline:
            return f"{setup} ... {punchline}"
        return "I had a joke ready, but it seems to have escaped me, sir."
    except Exception as e:
        logger.error(f"Joke API error: {e}")
        return "I'm afraid my joke generator is offline at the moment, sir."


@register("knowledge", "fact")
def random_fact() -> str:
    """Get a random useless fact."""
    try:
        resp = requests.get(
            "https://uselessfacts.jsph.pl/api/v2/facts/random",
            params={"language": "en"},
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        fact = data.get("text", "")
        if fact:
            return f"Here's an interesting fact: {_truncate(fact)}"
        return "I couldn't find a fact at the moment, sir."
    except Exception as e:
        logger.error(f"Random fact error: {e}")
        return "My fact database appears to be unavailable, sir."


@register("knowledge", "quote")
def quote_of_day() -> str:
    """Get an inspirational quote from ZenQuotes."""
    try:
        resp = requests.get(
            "https://zenquotes.io/api/random",
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        if data and isinstance(data, list):
            quote = data[0]
            text = quote.get("q", "")
            author = quote.get("a", "Unknown")
            if text:
                return f'"{text}" -- {author}'
        return "I couldn't retrieve a quote at the moment, sir."
    except Exception as e:
        logger.error(f"Quote API error: {e}")
        return "My quote service is unavailable right now, sir."


# ---------------------------------------------------------------------------
# Science & Math — Unit Conversion
# ---------------------------------------------------------------------------

_CONVERSIONS = {
    # (from_unit, to_unit): (multiplier, offset_add)
    # Distance
    ("miles", "km"): (1.60934, 0),
    ("km", "miles"): (0.621371, 0),
    ("feet", "meters"): (0.3048, 0),
    ("meters", "feet"): (3.28084, 0),
    ("inches", "cm"): (2.54, 0),
    ("cm", "inches"): (0.393701, 0),
    ("yards", "meters"): (0.9144, 0),
    ("meters", "yards"): (1.09361, 0),
    # Weight
    ("pounds", "kg"): (0.453592, 0),
    ("kg", "pounds"): (2.20462, 0),
    ("ounces", "grams"): (28.3495, 0),
    ("grams", "ounces"): (0.035274, 0),
    # Volume
    ("gallons", "liters"): (3.78541, 0),
    ("liters", "gallons"): (0.264172, 0),
    # Speed
    ("mph", "kph"): (1.60934, 0),
    ("kph", "mph"): (0.621371, 0),
}

# Aliases for unit names
_UNIT_ALIASES = {
    "mile": "miles", "kilometer": "km", "kilometers": "km",
    "kilometre": "km", "kilometres": "km",
    "foot": "feet", "meter": "meters", "metre": "meters", "metres": "meters",
    "inch": "inches", "centimeter": "cm", "centimeters": "cm",
    "centimetre": "cm", "centimetres": "cm",
    "yard": "yards",
    "pound": "pounds", "lb": "pounds", "lbs": "pounds",
    "kilogram": "kg", "kilograms": "kg", "kilo": "kg", "kilos": "kg",
    "ounce": "ounces", "oz": "ounces",
    "gram": "grams", "g": "grams",
    "gallon": "gallons", "liter": "liters", "litre": "liters",
    "litres": "liters",
    "fahrenheit": "fahrenheit", "celsius": "celsius",
    "f": "fahrenheit", "c": "celsius",
}


def _normalize_unit(unit: str) -> str:
    """Normalize a unit string to its canonical form."""
    unit = unit.lower().strip().rstrip(".")
    return _UNIT_ALIASES.get(unit, unit)


@register("knowledge", "convert")
def unit_convert(expression: str) -> str:
    """Convert units. Parses expressions like '5 miles to km'."""
    try:
        # Pattern: <number> <unit> to/in <unit>
        pattern = r"([\d.]+)\s+([a-zA-Z]+)\s+(?:to|in|into)\s+([a-zA-Z]+)"
        match = re.search(pattern, expression.strip(), re.IGNORECASE)

        if not match:
            return (
                "I couldn't parse that conversion, sir. "
                "Try something like '5 miles to km' or '100 fahrenheit to celsius'."
            )

        value = float(match.group(1))
        from_unit = _normalize_unit(match.group(2))
        to_unit = _normalize_unit(match.group(3))

        # Handle temperature conversions specially
        if from_unit == "fahrenheit" and to_unit == "celsius":
            result = (value - 32) * 5 / 9
            return f"{value:.1f} Fahrenheit is {result:.1f} Celsius."
        elif from_unit == "celsius" and to_unit == "fahrenheit":
            result = (value * 9 / 5) + 32
            return f"{value:.1f} Celsius is {result:.1f} Fahrenheit."

        conversion = _CONVERSIONS.get((from_unit, to_unit))
        if not conversion:
            return (
                f"I don't know how to convert {from_unit} to {to_unit}, sir. "
                "I support: miles/km, feet/meters, inches/cm, pounds/kg, "
                "ounces/grams, fahrenheit/celsius, gallons/liters, and mph/kph."
            )

        multiplier, _ = conversion
        result = value * multiplier
        return f"{value:g} {from_unit} is {result:.2f} {to_unit}."

    except ValueError:
        return "I couldn't parse the number in that conversion, sir."
    except Exception as e:
        logger.error(f"Unit conversion error: {e}")
        return f"Sorry, I had trouble with that conversion: {e}"


# ---------------------------------------------------------------------------
# Country/City Info
# ---------------------------------------------------------------------------

@register("knowledge", "country")
def country_info(country: str) -> str:
    """Get country info from the REST Countries API."""
    try:
        resp = requests.get(
            f"https://restcountries.com/v3.1/name/{country.strip()}",
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 404:
            return f"I couldn't find information about '{country}', sir."

        data = resp.json()
        if not data or not isinstance(data, list):
            return f"No data found for '{country}'."

        c = data[0]
        name = c.get("name", {}).get("common", country)
        capital_list = c.get("capital", [])
        capital = capital_list[0] if capital_list else "Unknown"
        population = c.get("population", 0)
        region = c.get("region", "Unknown")
        subregion = c.get("subregion", "")
        languages = c.get("languages", {})
        lang_names = ", ".join(languages.values()) if languages else "Unknown"
        currencies = c.get("currencies", {})
        currency_names = ", ".join(
            v.get("name", k) for k, v in currencies.items()
        ) if currencies else "Unknown"

        # Format population nicely
        if population >= 1_000_000_000:
            pop_str = f"{population / 1_000_000_000:.1f} billion"
        elif population >= 1_000_000:
            pop_str = f"{population / 1_000_000:.1f} million"
        elif population >= 1_000:
            pop_str = f"{population / 1_000:.1f} thousand"
        else:
            pop_str = str(population)

        region_str = f"{subregion}, {region}" if subregion else region

        return (
            f"{name}: capital is {capital}, population approximately {pop_str}. "
            f"Located in {region_str}. "
            f"Languages: {lang_names}. Currency: {currency_names}."
        )
    except Exception as e:
        logger.error(f"Country info error: {e}")
        return f"Sorry, I couldn't look up '{country}': {e}"


# ---------------------------------------------------------------------------
# Date/Time Utilities
# ---------------------------------------------------------------------------

# Major city to IANA timezone mapping
_CITY_TIMEZONES = {
    "new york": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "denver": "America/Denver",
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "rome": "Europe/Rome",
    "madrid": "Europe/Madrid",
    "amsterdam": "Europe/Amsterdam",
    "brussels": "Europe/Brussels",
    "vienna": "Europe/Vienna",
    "zurich": "Europe/Zurich",
    "moscow": "Europe/Moscow",
    "istanbul": "Europe/Istanbul",
    "dubai": "Asia/Dubai",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "shanghai": "Asia/Shanghai",
    "beijing": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "tokyo": "Asia/Tokyo",
    "seoul": "Asia/Seoul",
    "singapore": "Asia/Singapore",
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "auckland": "Pacific/Auckland",
    "toronto": "America/Toronto",
    "vancouver": "America/Vancouver",
    "mexico city": "America/Mexico_City",
    "sao paulo": "America/Sao_Paulo",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "cairo": "Africa/Cairo",
    "johannesburg": "Africa/Johannesburg",
    "cape town": "Africa/Johannesburg",
    "lagos": "Africa/Lagos",
    "nairobi": "Africa/Nairobi",
    "bangkok": "Asia/Bangkok",
    "jakarta": "Asia/Jakarta",
    "taipei": "Asia/Taipei",
    "kuala lumpur": "Asia/Kuala_Lumpur",
    "lisbon": "Europe/Lisbon",
    "dublin": "Europe/Dublin",
    "stockholm": "Europe/Stockholm",
    "oslo": "Europe/Oslo",
    "copenhagen": "Europe/Copenhagen",
    "helsinki": "Europe/Helsinki",
    "warsaw": "Europe/Warsaw",
    "prague": "Europe/Prague",
    "budapest": "Europe/Budapest",
    "athens": "Europe/Athens",
    "riyadh": "Asia/Riyadh",
    "doha": "Asia/Qatar",
    "honolulu": "Pacific/Honolulu",
    "anchorage": "America/Anchorage",
    "lima": "America/Lima",
    "bogota": "America/Bogota",
    "santiago": "America/Santiago",
}


@register("knowledge", "timezone")
def timezone_info(city: str) -> str:
    """Get the current time in a city using Python's zoneinfo."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        try:
            from backports.zoneinfo import ZoneInfo
        except ImportError:
            logger.error("zoneinfo module not available")
            return "Timezone support is not available on this system, sir."

    city_lower = city.lower().strip()
    tz_name = _CITY_TIMEZONES.get(city_lower)

    if not tz_name:
        # Try partial match
        for known_city, tz in _CITY_TIMEZONES.items():
            if city_lower in known_city or known_city in city_lower:
                tz_name = tz
                break

    if not tz_name:
        # Try using the WorldTimeAPI as fallback
        try:
            resp = requests.get(
                "https://worldtimeapi.org/api/timezone",
                timeout=REQUEST_TIMEOUT,
            )
            all_zones = resp.json()
            for zone in all_zones:
                if city_lower in zone.lower():
                    tz_name = zone
                    break
        except Exception:
            pass

    if not tz_name:
        available = ", ".join(
            name.title() for name in sorted(_CITY_TIMEZONES.keys())[:10]
        )
        return (
            f"I don't have timezone data for '{city}', sir. "
            f"I know cities like: {available}, and many more."
        )

    try:
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)
        time_str = now.strftime("%I:%M %p on %A, %B %d")
        return f"The current time in {city.title()} is {time_str}."
    except Exception as e:
        logger.error(f"Timezone calculation error: {e}")
        return f"Sorry, I couldn't determine the time for '{city}': {e}"


# Well-known date references
_KNOWN_DATES = {
    "christmas": (12, 25),
    "christmas day": (12, 25),
    "new year": (1, 1),
    "new years": (1, 1),
    "new year's": (1, 1),
    "new year's day": (1, 1),
    "new years day": (1, 1),
    "valentine's day": (2, 14),
    "valentines day": (2, 14),
    "valentine": (2, 14),
    "halloween": (10, 31),
    "independence day": (7, 4),
    "fourth of july": (7, 4),
    "st patrick's day": (3, 17),
    "st patricks day": (3, 17),
    "earth day": (4, 22),
    "labor day": (9, 1),       # approximate — first Monday
    "april fools": (4, 1),
    "april fool's day": (4, 1),
}


@register("knowledge", "days_until")
def days_until(date_str: str) -> str:
    """Calculate days until a given date or named event."""
    today = datetime.now().date()
    target_name = date_str.strip()
    target_date = None

    # Check known dates first
    known = _KNOWN_DATES.get(target_name.lower())
    if known:
        month, day = known
        target_date = today.replace(month=month, day=day)
        # If the date has already passed this year, use next year
        if target_date < today:
            target_date = target_date.replace(year=today.year + 1)
    else:
        # Try parsing various date formats
        date_formats = [
            "%B %d %Y",       # March 15 2026
            "%B %d, %Y",      # March 15, 2026
            "%b %d %Y",       # Mar 15 2026
            "%b %d, %Y",      # Mar 15, 2026
            "%m/%d/%Y",       # 03/15/2026
            "%d/%m/%Y",       # 15/03/2026
            "%Y-%m-%d",       # 2026-03-15
            "%B %d",          # March 15 (assume current/next year)
            "%b %d",          # Mar 15
            "%m/%d",          # 03/15
        ]

        for fmt in date_formats:
            try:
                parsed = datetime.strptime(target_name, fmt).date()
                # If no year was in the format, set to this/next year
                if "%Y" not in fmt:
                    parsed = parsed.replace(year=today.year)
                    if parsed < today:
                        parsed = parsed.replace(year=today.year + 1)
                target_date = parsed
                break
            except ValueError:
                continue

    if target_date is None:
        return (
            f"I couldn't parse the date '{target_name}', sir. "
            "Try formats like 'Christmas', 'March 15 2026', or '03/15/2026'."
        )

    delta = (target_date - today).days

    if delta == 0:
        return f"{target_name} is today!"
    elif delta == 1:
        return f"{target_name} is tomorrow!"
    elif delta < 0:
        return f"{target_name} was {abs(delta)} days ago."
    else:
        weeks = delta // 7
        remaining_days = delta % 7
        if weeks > 0 and remaining_days > 0:
            extra = f" (that's {weeks} weeks and {remaining_days} days)"
        elif weeks > 0:
            extra = f" (that's exactly {weeks} weeks)"
        else:
            extra = ""
        return f"There are {delta} days until {target_name}{extra}."
