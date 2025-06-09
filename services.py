import requests
import time
from typing import Optional, Tuple

class GeocodingService:
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.reverse_url = "https://nominatim.openstreetmap.org/reverse"
        
    def geocode_address(self, address: str, city: str = "Astana", country: str = "Kazakhstan") -> Optional[Tuple[float, float]]:
        try:
            full_address = f"{address}, {city}, {country}"
            
            params = {
                'q': full_address,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'kz', 
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': 'EduPlatform-Astana/1.0'  
            }
            
            response = requests.get(self.base_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
                result = data[0]
                lat = float(result['lat'])
                lon = float(result['lon'])
                
                if 50.5 <= lat <= 52.0 and 70.0 <= lon <= 72.5:
                    return (lat, lon)
                else:
                    print(f"Coordinates outside Astana area: {lat}, {lon}")
                    return None
            
            return None
            
        except requests.RequestException as e:
            print(f"Geocoding API error: {e}")
            return None
        except (ValueError, KeyError) as e:
            print(f"Geocoding parse error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected geocoding error: {e}")
            return None
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        try:
            params = {
                'lat': latitude,
                'lon': longitude,
                'format': 'json',
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': 'EduPlatform-Astana/1.0'
            }
            
            response = requests.get(self.reverse_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'display_name' in data:
                return data['display_name']
            
            return None
            
        except Exception as e:
            print(f"Reverse geocoding error: {e}")
            return None
    
    def get_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        import math
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        r = 6371
        
        return c * r

ASTANA_LANDMARKS = {
    'bayterek': (51.1282, 71.4306),
    'hazrat_sultan_mosque': (51.1244, 71.4015),
    'khan_shatyr': (51.1327, 71.4047),
    'palace_of_peace': (51.0951, 71.4156),
    'city_center': (51.1605, 71.4704),
    'airport': (51.0244, 71.4669)
}

def get_astana_bounds():
    return {
        'north': 51.25,
        'south': 50.95,
        'east': 71.65,
        'west': 71.25
    }