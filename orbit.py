import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

inc = 97.88
TARGET_LAT, TARGET_LON = 51.9973, 4.368927
km_lead = 20
km_trail = 10
swath_km = 12

def getPositions(lat1,lon1, lat2,lon2, swath_km):
    # Calculate the distance between the two points
    distance = np.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2) * 111.0  # Convert degrees to km
    # Lin interpolate positions along the path
    num_images = int(np.ceil(distance / swath_km))+1
    lats = np.linspace(lat1, lat2, num_images)
    lons = np.linspace(lon1, lon2, num_images)    
    return lats, lons

def findRel(lat1, lon1, inc, dis):
    # Calculate the change in latitude and longitude based on the distance and inclination
    inc= inc + 90
    delta_lat = dis * np.cos(np.radians(inc)) / 111.0  # Convert km to degrees latitude
    delta_lon = dis * np.sin(np.radians(inc)) / (111.0 * np.cos(np.radians(lat1)))  # Convert km to degrees longitude

    # Calculate the starting point
    start_lat = lat1 - delta_lat
    start_lon = lon1 - delta_lon

    return start_lat, start_lon

def plotPositions(lats, lons, swath_km=8, square_km=12):
    plt.figure(figsize=(10, 8))
    plt.plot(lons, lats, marker='o', linestyle='-', color='blue', label='Satellite path')
    
    # Draw squares around each point
    for lat, lon in zip(lats, lons):
        # Convert km to degrees
        half_swath_lat = swath_km / (2 * 111.0)
        half_swath_lon = swath_km / (2 * 111.0 * np.cos(np.radians(lat)))
        half_square_lat = square_km / (2 * 111.0)
        half_square_lon = square_km / (2 * 111.0 * np.cos(np.radians(lat)))
        
        # Draw swath_km square
        swath_rect = Rectangle(
            (lon - half_swath_lon, lat - half_swath_lat),
            swath_km / (111.0 * np.cos(np.radians(lat))),
            swath_km / 111.0,
            fill=False, edgecolor='green', linewidth=1, alpha=0.6, linestyle='--'
        )
        plt.gca().add_patch(swath_rect)
        
        # Draw square_km square
        square_rect = Rectangle(
            (lon - half_square_lon, lat - half_square_lat),
            square_km / (111.0 * np.cos(np.radians(lat))),
            square_km / 111.0,
            fill=False, edgecolor='red', linewidth=1, alpha=0.6, linestyle=':'
        )
        plt.gca().add_patch(square_rect)
    
    plt.title('Satellite Image Positions')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.legend(['Satellite path', f'Swath {swath_km}km', f'Square {square_km}km'])
    plt.grid()
    plt.show()
    

LAT_START, LON_START = findRel(TARGET_LAT, TARGET_LON, inc, -km_lead)
LAT_END, LON_END = findRel(TARGET_LAT, TARGET_LON, inc, km_trail)
lats, lons = getPositions(LAT_START, LON_START, LAT_END, LON_END, swath_km=swath_km)
print(f"Start: ({LAT_START:.6f}, {LON_START:.6f}), End: ({LAT_END:.6f}, {LON_END:.6f}), Total distance: {np.sqrt((LAT_END - LAT_START)**2 + (LON_END - LON_START)**2) * 111.0:.2f} km")
print(f"Number of images: {len(lats)}")
df_images = pd.DataFrame({
    'image_num': range(1, len(lats)+1),
    'center_lat': lats,
    'center_lon': lons,
    'swath_km': swath_km
})

if __name__ == "__main__":
    plotPositions(lats, lons, swath_km=swath_km, square_km=8)
    print(df_images)
  