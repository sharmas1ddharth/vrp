# import sqlite3

# # Connect to SQLite database (or create it if it doesn't exist)


# def save_data(request, response, job_id):
#     conn = sqlite3.connect('route_data.db')
#     cursor = conn.cursor()
#     cursor.execute('''
#     CREATE TABLE IF NOT EXISTS ROUTE_DATA (
#         jobid TEXT PRIMARY KEY,
#         request TEXT NOT NULL,
#         response TEXT)''')

#     data = [job_id, request, response]

#     cursor.executemany('''
#     INSERT OR IGNORE INTO ROUTE_DATA (id, name, age, email)
#     VALUES (?, ?, ?, ?)
#     ''', data)
#     conn.commit()
#     conn.close()
