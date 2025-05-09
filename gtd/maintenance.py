
from gtd.extensions import Report
from gtd.config import get_config_str, get_config_bool
from gtd.drive import Spreadsheet
import datetime
from gtd.style import section, table, paragraph, items, green, red

def add_extensions(report: Report):
    """
    Reads table for maintenance and adds items with unmaintained items
    """
    report.add(section("Maintenance"))
    import pandas as pd 
    maintenance_file_path = get_config_str("maintenance_file", "", "Path to the maintenance file")
    sheet_name = get_config_str("maintenance_sheet", "maintenance", "Sheet name in the maintenance file")
    last_maintenance_column = get_config_str("last_maintenance_column", "Last maintenance", "Column name for last maintenance")
    frequency_column = get_config_str("frequency_column", "Frequency (days)", "Column name for frequency")
    item_column = get_config_str("item_column", "Item", "Column name for item")
    operation_column = get_config_str("operation_column", "Operation", "Column name for operation")
    if maintenance_file_path == "":
        return 
    maintenance = Spreadsheet(maintenance_file_path.replace("drive://", ""))
    df = maintenance.open_pandas(sheet_name)
    if df is None:
        return
    total = len(df)
    df[last_maintenance_column] = df[last_maintenance_column].apply(pd.to_datetime)
    df[frequency_column] = df[frequency_column].apply(int)
    df[frequency_column] = df[frequency_column].apply(lambda x: datetime.timedelta(days=x))
    df = df[df[last_maintenance_column] + df[frequency_column] < datetime.datetime.now()]
    needs_maintenance = len(df)
    ratio = needs_maintenance / total
    if ratio >= 0.2:
        report.add(paragraph("Maintenance percentage: " + red(f"{1-ratio:.0%}")))
    else:
        report.add(paragraph("Maintenance percentage: " + green(f"{1-ratio:.0%}")))
    if df.empty:
        report.add(paragraph("No maintenance required"))
        return
    for item, operations in df.groupby(item_column):
        report.add(section(item, 1))
        report.add(items(operations[operation_column].tolist()))
    