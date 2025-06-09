from flask import Blueprint, current_app
from database import db
from models import Center
from services import GeocodingService

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/geocode-centers')
def geocode_existing_centers():
    if not current_app.debug:
        return "This function is only available in debug mode", 403
    
    geocoding_service = GeocodingService()
    centers = Center.query.filter(Center.latitude.is_(None)).all()
    
    updated_count = 0
    for center in centers:
        try:
            coordinates = geocoding_service.geocode_address(center.address, "Astana", "Kazakhstan")
            if coordinates:
                center.latitude, center.longitude = coordinates
                updated_count += 1
        except Exception as e:
            print(f"Error geocoding {center.center_name}: {e}")
    
    if updated_count > 0:
        db.session.commit()
        return f"Successfully geocoded {updated_count} centers"
    else:
        return "No centers updated"