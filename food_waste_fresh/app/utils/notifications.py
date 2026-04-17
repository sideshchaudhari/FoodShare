from app.models.db import mysql

def add_notification(user_id, message, ntype="info"):
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO notifications (user_id, message, type)
        VALUES (%s, %s, %s)
    """, (user_id, message, ntype))
    mysql.connection.commit()
    cur.close()