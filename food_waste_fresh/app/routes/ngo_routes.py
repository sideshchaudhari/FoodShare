from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.models.db import mysql
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)

ngo_bp = Blueprint('ngo', __name__, url_prefix='/ngo')

@ngo_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'ngo':
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()

    # Stats
    cur.execute("SELECT COUNT(*) FROM donations WHERE status='Pending'")
    pending = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM donations
        WHERE accepted_by=%s
    """, (session['user_id'],))
    accepted = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM donations
        WHERE accepted_by=%s AND status='Picked'
    """, (session['user_id'],))
    picked = cur.fetchone()[0]

    cur.close()

    return render_template(
        'ngo/dashboard.html',
        pending=pending,
        accepted=accepted,
        picked=picked
    )


from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from flask import request

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance in KM using Haversine formula
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c  # Earth radius in KM


@ngo_bp.route('/available-donations')
def available_donations():
    if 'user_id' not in session or session.get('role') != 'ngo':
        return redirect(url_for('auth.login'))

    # NGO location (TEMP: later fetch from NGO profile)
    NGO_LAT = 19.0760    # example: Mumbai
    NGO_LNG = 72.8777

    # Filters
    city = request.args.get('city', '')
    urgency = request.args.get('urgency', '')
    max_hours = request.args.get('max_hours', '')
    sort_by = request.args.get('sort_by', 'ai')

    query = """
        SELECT id, food_title, quantity_kg, city, urgency,
               expiry_time, packaging_condition,
               latitude, longitude
        FROM donations
        WHERE status='Pending'
    """
    params = []

    if city:
        query += " AND city=%s"
        params.append(city)

    if urgency:
        query += " AND urgency=%s"
        params.append(urgency)

    cur = mysql.connection.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()

    now = datetime.now()
    results = []

    for r in rows:
        expiry = r[5]
        hours_left = (expiry - now).total_seconds() / 3600 if expiry else 999

        if max_hours and hours_left > float(max_hours):
            continue

        # --- Distance ---
        distance_km = None
        if r[7] and r[8]:
            distance_km = calculate_distance(
                NGO_LAT, NGO_LNG,
                float(r[7]), float(r[8])
            )

        # --- AI SCORE ---
        score = 0

        if r[4] == 'Immediate':
            score += 50
        elif r[4] == 'High':
            score += 30
        else:
            score += 10

        if hours_left <= 2:
            score += 40
        elif hours_left <= 6:
            score += 25
        elif hours_left <= 12:
            score += 10

        if r[6] == 'Good':
            score += 15

        if distance_km is not None:
            if distance_km <= 5:
                score += 25
            elif distance_km <= 10:
                score += 15

        results.append({
            "data": r,
            "score": score,
            "hours_left": round(hours_left, 1),
            "distance": round(distance_km, 1) if distance_km else None
        })

    # --- SORTING ---
    if sort_by == 'distance':
        results.sort(key=lambda x: x["distance"] if x["distance"] is not None else 999)
    elif sort_by == 'expiry':
        results.sort(key=lambda x: x["hours_left"])
    else:  # AI relevance
        results.sort(key=lambda x: x["score"], reverse=True)

    return render_template(
        'ngo/available_donations.html',
        donations=results,
        city=city,
        urgency=urgency,
        max_hours=max_hours,
        sort_by=sort_by
    )



@ngo_bp.route('/accept-donation/<int:donation_id>')
def accept_donation(donation_id):
    if 'user_id' not in session or session.get('role') != 'ngo':
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()


    cur.execute("""
            SELECT full_name 
            FROM users 
            WHERE id=%s
        """, (session['user_id'],))

    ngo = cur.fetchone()
    ngo_name = ngo[0] if ngo else "Unknown NGO"
    cur.execute("""
        SELECT donor_id 
        FROM donations 
        WHERE id=%s
    """, (donation_id,))

    result = cur.fetchone()

    if not result:
        cur.close()
        return "Donation not found", 404

    donor_id = result[0]

    # 2. Accept donation
    cur.execute("""
        UPDATE donations
        SET status='Accepted',
            accepted_by=%s,
            accepted_at=NOW()
        WHERE id=%s AND status='Pending'
    """, (session['user_id'], donation_id))

    mysql.connection.commit()
    cur.execute("""
                    SELECT full_name 
                    FROM users 
                    WHERE id=%s
                """, (donor_id,))
    user=cur.fetchone()
    donor_name = user[0] if user else None
    # 3. Insert notification for donor
    cur.execute("""
        INSERT INTO notifications (user_id, message, type)
        VALUES (%s, %s, %s)
    """, (
        donor_id,
        f"Dear {donor_name}, Your donation has been accepted by {ngo_name}",
        "success"
    ))

    mysql.connection.commit()

    cur.close()

    return render_template(
        'ngo/accept_success.html',
        donation_id=donation_id
    )


@ngo_bp.route('/my-donations')
def my_donations():
    if 'user_id' not in session or session.get('role') != 'ngo':
        return redirect(url_for('auth.login'))

    ngo_id = session['user_id']

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT
            id,
            food_title,
            quantity_kg,
            city,
            contact_name,
            contact_phone,
            status,
            expiry_time
        FROM donations
        WHERE accepted_by = %s
        ORDER BY accepted_at DESC
    """, (ngo_id,))
    donations = cur.fetchall()
    cur.close()

    return render_template(
        'ngo/my_donations.html',
        donations=donations
    )


@ngo_bp.route('/mark-picked/<int:donation_id>')
def mark_picked(donation_id):
    if 'user_id' not in session or session.get('role') != 'ngo':
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE donations
        SET status='Picked'
        WHERE id=%s AND accepted_by=%s
    """, (donation_id, session['user_id']))
    cur.execute("""
            SELECT donor_id 
            FROM donations 
            WHERE id=%s
        """, (donation_id,))

    result = cur.fetchone()
    if not result:
        cur.close()
        return "Donation not found", 404
    donor_id=result[0]
    cur.execute("""
                SELECT full_name 
                FROM users 
                WHERE id=%s
            """, (session['user_id'],))

    ngo = cur.fetchone()
    ngo_name = ngo[0] if ngo else "Unknown NGO"
    cur.execute("""
                        SELECT full_name 
                        FROM users 
                        WHERE id=%s
                    """, (donor_id,))
    user = cur.fetchone()
    donor_name = user[0] if user else None
    cur.execute("""
            INSERT INTO notifications (user_id, message, type)
            VALUES (%s, %s, %s)
        """, (
        donor_id,
        f"Dear {donor_name}, Your donation has been picked up By {ngo_name}",
        "success"
    ))
    mysql.connection.commit()
    cur.close()

    flash("Donation marked as picked.", "success")
    return redirect(url_for('ngo.my_donations'))


@ngo_bp.route('/donation/<int:donation_id>')
def donation_detail(donation_id):
    if 'user_id' not in session or session.get('role') != 'ngo':
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT
            food_title, food_type, food_category, quantity_kg, servings,
            urgency, expiry_time,
            pickup_address, city, state, pincode,
            contact_name, contact_phone,
            packaging_condition, temperature_condition,
            pickup_type, accessibility_notes,
            latitude, longitude,
            status
        FROM donations
        WHERE id=%s
    """, (donation_id,))

    donation = cur.fetchone()
    cur.close()

    if not donation:
        flash("Donation not found.", "danger")
        return redirect(url_for('ngo.available_donations'))

    # Safely prepare map bounds
    lat = donation[17]
    lng = donation[18]

    map_data = None
    if lat and lng:
        lat = float(lat)
        lng = float(lng)
        map_data = {
            "lat": lat,
            "lng": lng,
            "lat_min": lat - 0.01,
            "lat_max": lat + 0.01,
            "lng_min": lng - 0.01,
            "lng_max": lng + 0.01
        }

    return render_template(
        'ngo/donation_detail.html',
        donation=donation,
        donation_id=donation_id,
        map_data=map_data
    )

@ngo_bp.route('/mark-completed/<int:donation_id>')
def mark_completed(donation_id):
    if 'user_id' not in session or session.get('role') != 'ngo':
        return redirect(url_for('auth.login'))

    ngo_id = session['user_id']

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE donations
        SET status = 'Completed'
        WHERE id = %s
          AND accepted_by = %s
          AND status = 'Picked'
    """, (donation_id, ngo_id))
    cur.execute("""
                SELECT donor_id 
                FROM donations 
                WHERE id=%s
            """, (donation_id,))

    result = cur.fetchone()
    if not result:
        cur.close()
        return "Donation not found", 404
    donor_id = result[0]
    cur.execute("""
                    SELECT full_name 
                    FROM users 
                    WHERE id=%s
                """, (session['user_id'],))

    ngo = cur.fetchone()
    ngo_name = ngo[0] if ngo else "Unknown NGO"
    cur.execute("""
                            SELECT full_name 
                            FROM users 
                            WHERE id=%s
                        """, (donor_id,))
    user = cur.fetchone()
    donor_name = user[0] if user else None
    cur.execute("""
                INSERT INTO notifications (user_id, message, type)
                VALUES (%s, %s, %s)
            """, (
        donor_id,
        f"Dear {donor_name}, Your donation has been Completed By {ngo_name}",
        "success"
    ))
    mysql.connection.commit()
    cur.close()

    flash("Donation marked as completed.", "success")
    return redirect(url_for('ngo.my_donations'))

from flask import send_file

@ngo_bp.route('/download_report/<int:donation_id>')
def download_report(donation_id):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            d.id, d.food_title, d.food_type, d.quantity_kg,
            d.expiry_time, d.pickup_address, d.city, d.state, d.pincode,
            d.latitude, d.longitude,
            u.full_name, d.contact_phone, d.created_at
        FROM donations d
        JOIN users u ON d.donor_id = u.id
        WHERE d.id = %s
    """, (donation_id,))

    d = cur.fetchone()

    if not d:
        return "Not found", 404

    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    elements = []

    # ================= HEADER =================
    elements.append(Paragraph(
        "<font size=20 color='green'><b>FoodShare NGO Report</b></font>",
        styles['Title']
    ))
    elements.append(Paragraph(
        "<font size=10 color='grey'>Smart Food Redistribution System</font>",
        styles['Normal']
    ))
    elements.append(Spacer(1, 10))

    # Divider
    elements.append(Table([[""]], colWidths=[500], style=[
        ('BACKGROUND', (0, 0), (-1, -1), colors.green),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3)
    ]))
    elements.append(Spacer(1, 15))

    # ================= META =================
    meta = Table([
        ["Report ID:", d[0]],
        ["Generated On:", str(d[13])]
    ], colWidths=[150, 300])

    meta.setStyle([
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold')
    ])

    elements.append(meta)
    elements.append(Spacer(1, 15))

    # ================= FUNCTION =================
    def section(title, data):
        elements.append(Paragraph(
            f"<font color='darkgreen'><b>{title}</b></font>",
            styles['Heading3']
        ))
        table = Table(data, colWidths=[150, 350])
        table.setStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 8)
        ])
        elements.append(table)
        elements.append(Spacer(1, 12))

    # ================= DONOR =================
    section("Donor Details", [
        ["Name", d[11]],
        ["Contact", d[12]]
    ])

    # ================= FOOD =================
    section("Food Details", [
        ["Title", d[1]],
        ["Type", d[2]],
        ["Quantity", f"<b>{d[3]} kg</b>"],
        ["Expiry", str(d[4])]
    ])

    # ================= LOCATION =================
    address = f"{d[5]}, {d[6]}, {d[7]} - {d[8]}"
    section("Pickup Location", [
        ["Address", address]
    ])

    # ================= REAL MAP (OpenStreetMap) =================
    from reportlab.platypus import Image
    import urllib.request
    import io

    lat = d[9]
    lng = d[10]

    if lat and lng:
        try:
            lat = float(lat)
            lng = float(lng)
            # OpenStreetMap static map URL
            map_url = f"https://staticmap.openstreetmap.de/staticmap.php?center={lat},{lng}&zoom=15&size=600x300&markers={lat},{lng},red-pushpin"

            # Download image directly into memory
            response = urllib.request.urlopen(map_url)
            img_data = response.read()
            img_buffer = io.BytesIO(img_data)

            # Add map to PDF
            elements.append(Paragraph(
                "<font color='darkgreen'><b>Pickup Location Map</b></font>",
                styles['Heading3']
            ))
            elements.append(Spacer(1, 10))
            elements.append(Image(img_buffer, width=450, height=250))

        except Exception as e:
            print("Error downloading map:", e)
            elements.append(Paragraph("Map could not be loaded", styles['Normal']))
    # ================= IMPACT =================
    people = int(d[3] * 3)
    section("Impact Analysis", [
        ["Estimated People Fed", f"{people}"],
        ["Status", "Accepted by NGO"]
    ])

    # ================= FOOTER =================
    elements.append(Spacer(1, 20))
    elements.append(Table([[""]], colWidths=[500], style=[
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('TOPPADDING', (0, 0), (-1, -1), 1)
    ]))

    elements.append(Spacer(1, 5))
    elements.append(Paragraph(
        "<i>Generated by FoodShare System | Reducing Food Waste, Saving Lives</i>",
        styles['Normal']
    ))

    # ================= BUILD =================
    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"NGO_Report_{donation_id}.pdf",
        mimetype='application/pdf'
    )