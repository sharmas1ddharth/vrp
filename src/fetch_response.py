import sqlite3

def fetch_response(job_id):
    connection = sqlite3.connect('route_data.db')
    cursor = connection.cursor()
    print(f"SELECT response FROM ROUTE_DATA where jobid='{job_id}'")
    cursor.execute(f"SELECT response FROM ROUTE_DATA where jobid='{job_id}'")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return rows[0][0]
