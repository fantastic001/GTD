
from gtd.extensions import Report
from gtd.config import get_config_str, get_config_bool
from gtd.drive import Spreadsheet
import datetime
from gtd.style import section, table

def add_extensions(report: Report):
    """
    Reads meals from ods file stored locally and returns a schedule for the next 7 days
    """
    report.add(section("Meals"))
    import pandas as pd 
    meals = ["Breakfast", "Lunch", "Dinner", "Snack"]
    meal_file_path = get_config_str("meals", "", "Path to meals file")
    df = {}
    if meal_file_path.startswith("drive://"):
        meal_file_path = meal_file_path.replace("drive://", "")
        for m in meals:
            df[m] = Spreadsheet(meal_file_path).open_pandas(m)
    else:
        df = {m: pd.read_excel(meal_file_path, sheet_name=m) for m in meals}
    result = []
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for i, day in enumerate(weekdays):
        day_in_year = datetime.date.today().isocalendar().week * 7 + i
        meals_for_day = {m: df[m].iloc[day_in_year % len(df[m])] for m in meals}
        table_records = [
            {
                "Meal": m,
                "Name": meals_for_day[m]["Name"],
                "Supplier": meals_for_day[m]["Supplier"],
            } for m in meals
        ]
        report.add(section(day, level=1))
        report.add(table(table_records))
        
