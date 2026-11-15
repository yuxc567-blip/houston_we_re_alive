import sqlite3
import numpy as np


class PreventionDatabase:

    def __init__(self, filename="prevention.db"):

        self.connection = sqlite3.connect(filename)

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS prevention_records (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                timestamp TEXT NOT NULL,

                indicator TEXT NOT NULL,

                intervention TEXT NOT NULL,

                error REAL NOT NULL,

                prevention_amount REAL NOT NULL

            )
        """)

        self.connection.commit()

    # --------------------------------------------------------
    # STORE HISTORICAL DATA
    # --------------------------------------------------------

    def add_record(
        self,
        timestamp,
        indicator,
        intervention,
        error,
        prevention_amount
    ):

        self.connection.execute("""
            INSERT INTO prevention_records (

                timestamp,
                indicator,
                intervention,
                error,
                prevention_amount

            )

            VALUES (?, ?, ?, ?, ?)

        """, (
            timestamp,
            indicator,
            intervention,
            error,
            prevention_amount
        ))

        self.connection.commit()

    # --------------------------------------------------------
    # RETRIEVE HISTORICAL DATA
    # --------------------------------------------------------

    def get_records(self, indicator, intervention):

        cursor = self.connection.execute("""
            SELECT error, prevention_amount

            FROM prevention_records

            WHERE indicator = ?
            AND intervention = ?

            ORDER BY timestamp ASC

        """, (indicator, intervention))

        return cursor.fetchall()

    def close(self):

        self.connection.close()





class LinearRegression:

    def __init__(self, database, minimum_samples=10):

        self.database = database

        self.minimum_samples = minimum_samples

    # --------------------------------------------------------
    # CALCULATE REGRESSION
    # --------------------------------------------------------

    def analyze(self, indicator, intervention):

        records = self.database.get_records(
            indicator,
            intervention
        )

        if len(records) < self.minimum_samples:
            return None

        # Separate X and Y values.
        x = np.array(
            [record[0] for record in records],
            dtype=float
        )

        y = np.array(
            [record[1] for record in records],
            dtype=float
        )

        # Error must vary to establish a relationship.
        if np.ptp(x) == 0:
            return None

        # Calculate regression coefficients.
        slope, intercept = np.polyfit(x, y, 1)

        # Calculate predicted values.
        predicted = slope * x + intercept

        # Calculate R-squared.
        ss_res = np.sum((y - predicted) ** 2)

        ss_tot = np.sum((y - np.mean(y)) ** 2)

        if ss_tot == 0:
            return None

        r_squared = 1 - (ss_res / ss_tot)

        return {
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared,
            "samples": len(x),
            "min_error": float(np.min(x)),
            "max_error": float(np.max(x))
        }

    # --------------------------------------------------------
    # ESTIMATE PREVENTION AMOUNT
    # --------------------------------------------------------

    def predict(self, model, error):

        if model is None:
            return None

        # Only interpolate within historical observations.
        if not (
            model["min_error"] <= error
            <= model["max_error"]
        ):
            return None

        amount = (
            model["slope"] * error
            + model["intercept"]
        )

        return amount



class Prevention:

    def __init__(
        self,
        database,
        prevention_plans,
        r2_threshold=0.85
    ):

        self.database = database

        self.regression = LinearRegression(database)

        self.prevention_plans = prevention_plans

        self.r2_threshold = r2_threshold

    # --------------------------------------------------------
    # GENERATE RECOMMENDATION
    # --------------------------------------------------------

    def recommend(self, indicator, error, urgency):

        # Retrieve indicator-specific plan.
        plan = self.prevention_plans.get(indicator)

        if plan is None:
            return "No prevention plan available."

        intervention = plan["intervention"]

        unit = plan["unit"]

        # Predefined recommendation.
        fallback = plan["recommendations"].get(
            urgency,
            "Continue routine monitoring."
        )

        # 1. Calculate regression.
        model = self.regression.analyze(
            indicator,
            intervention
        )

        # 2. Check whether regression is applicable.
        if model is None:

            return fallback

        if model["r_squared"] < self.r2_threshold:

            return fallback

        # 3. Predict prevention amount.
        amount = self.regression.predict(
            model,
            error
        )

        if amount is None:

            return fallback

        # 4. Check independently validated limits.
        minimum = plan["minimum_amount"]
        maximum = plan["maximum_amount"]

        if not minimum <= amount <= maximum:

            return fallback

        # 5. Return adaptive recommendation.
        return (
            f"Recommended intervention: {intervention}\n"
            f"Estimated amount: {amount:.2f} {unit}\n"
            f"Regression R²: {model['r_squared']:.3f}\n"
            f"Historical samples: {model['samples']}"
        )



PREVENTION_PLANS = {

    "bone_density": {

        "intervention": "vitamin_D",

        "unit": "IU/day",

        # Must be established by validated clinical guidance.
        "minimum_amount": 0,
        "maximum_amount": 0,

        "recommendations": {

            "LOW": (
                "Maintain balanced nutrition "
                "and routine bone-health monitoring."
            ),

            "MEDIUM": (
                "Review nutritional status and "
                "consult a healthcare professional."
            ),

            "HIGH": (
                "Arrange a prompt clinical assessment "
                "for appropriate intervention."
            )
        }
    }
}


# Initialize database.
database = PreventionDatabase()

# Initialize prevention.
prevention = Prevention(
    database,
    PREVENTION_PLANS
)

# Example input from HealthController.
'''result = prevention.recommend(
    indicator="bone_density",
    error=0.06,
    urgency="MEDIUM"
)

print(result)'''