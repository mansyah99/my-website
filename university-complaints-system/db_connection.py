import pyodbc

def get_db_connection():
    conn = pyodbc.connect(
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-ANS3451;"
        "DATABASE=UniversityComplaintsDB;"
        "Trusted_Connection=yes;"
    )
    return conn