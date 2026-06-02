import math
from sgp4.api import Satrec, jday
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
# ── Low-level ECI → LLA ───────────────────────────────────────────────────────
# Month 3, day 22 is the best pass (error: 3.0997 km
def gmst(jd_full):
    """Greenwich Mean Sidereal Time (radians) for a Julian date."""
    T = (jd_full - 2451545.0) / 36525.0
    g = (280.46061837
         + 360.98564736629 * (jd_full - 2451545.0)
         + T * T * (0.000387933 - T / 38710000.0))
    return math.radians(g % 360)


def eci_to_lla(r_km, jd_full):
    """ECI position vector → (lat_deg, lon_deg, alt_km)."""
    x, y, z = r_km
    g = gmst(jd_full)
    lon = math.degrees(math.atan2(y, x) - g)
    lon = (lon + 180) % 360 - 180
    r   = math.sqrt(x**2 + y**2 + z**2)
    lat = math.degrees(math.asin(z / r))
    alt = r - 6371.0
    return lat, lon, alt


# ── Core propagation ──────────────────────────────────────────────────────────

def propagate_pass(tle1, tle2, start_jd, start_jdf, duration_s, dt_s=1.0):
    """
    Propagate a satellite from start_jd over duration_s seconds.

    Returns a list of dicts:
        {"t": elapsed_s, "lat": deg, "lon": deg, "alt": km}
    None entries are inserted where sgp4 returns an error.
    """
    sat = Satrec.twoline2rv(tle1, tle2)
    positions = []
    steps = int(duration_s / dt_s)

    for i in range(steps):
        t_s  = i * dt_s
        jd_i = start_jd + t_s / 86400.0
        e, r, _ = sat.sgp4(jd_i, start_jdf)
        if e != 0:
            positions.append(None)
            continue
        lat, lon, alt = eci_to_lla(r, jd_i + start_jdf)
        positions.append({"t": t_s, "lat": lat, "lon": lon, "alt": alt})

    return positions


# ── Pass finder ───────────────────────────────────────────────────────────────

def find_pass_over(tle1, tle2, target_lat, target_lon,
                   year, month, day, search_hours=24):
    """
    Scan `search_hours` starting at midnight on the given date and return
    the Julian date of closest approach to (target_lat, target_lon).

    Returns (jd, jdf) ready to pass into propagate_pass().
    """
    sat = Satrec.twoline2rv(tle1, tle2)
    jd0, jdf0 = jday(year, month, day, 0, 0, 0.0)

    best_jd, best_dist = jd0, 999.0
    steps = search_hours * 3600  # 1-second resolution

    for i in range(steps):
        jd_i = jd0 + i / 86400.0
        e, r, _ = sat.sgp4(jd_i, jdf0)
        if e != 0:
            continue
        lat, lon, _ = eci_to_lla(r, jd_i + jdf0)
        dist = math.sqrt((lat - target_lat)**2 + (lon - target_lon)**2)
        if dist < best_dist:
            best_dist = dist
            best_jd   = jd_i

    # Start 45 s before closest approach so Delft is centred in the pass
    return best_jd - 45 / 86400.0, jdf0


# ── Convenience: full Delft pass ──────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2)**2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2)**2)
    return R * 2 * math.asin(math.sqrt(a))


DEFAULT_TLE1 = "1 99999U 24001A   24167.50000000  .00000000  00000-0  00000-0 0  9999"
DEFAULT_TLE2 = "2 99999  97.5000  90.0000 0001000  90.0000 270.0000 15.19000000 00001"

DELFT_LAT, DELFT_LON = 52.0116, 4.3571


def delft_pass(tle1=DEFAULT_TLE1, tle2=DEFAULT_TLE2,
               year=2026, month=5, day=26,
               duration_s=90, dt_s=1.0):
    """
    Returns the propagated positions for a pass over Delft.
    Convenience wrapper around find_pass_over + propagate_pass.
    """
    jd, jdf = find_pass_over(tle1, tle2, DELFT_LAT, DELFT_LON,
                              year, month, day)
    return propagate_pass(tle1, tle2, jd, jdf, duration_s, dt_s)


# Get the best pass: Month 3, Day 22
positions = delft_pass(month=3, day=22, duration_s=90)
valid = [p for p in positions if p is not None]

# Find closest approach
closest = min(valid, key=lambda p: math.sqrt(
    (p['lat'] - DELFT_LAT)**2 + (p['lon'] - DELFT_LON)**2))
closest_time = closest['t']

traj_window = [p for p in valid if closest_time - 5 <= p['t'] <= closest_time + 2]

# Create dataframe with trajectory data
df = pd.DataFrame(traj_window)
df['time_rel'] = df['t'] - closest_time  # Time relative to closest approach
df['dist_to_delft'] = df.apply(
    lambda row: haversine(row['lat'], row['lon'], DELFT_LAT, DELFT_LON), 
    axis=1
)

# Calculate image coverage positions (8km x 8km swaths)
swath_km = 8
step_lat = swath_km / 111.0

# Calculate how many steps fit across the satellite pass
# Use the satellite's ground track displacement
lat_min, lat_max = df['lat'].min(), df['lat'].max()
lat_range = lat_max - lat_min
num_steps = max(1, int(lat_range / step_lat) + 1)

# Create image positions by sampling the actual trajectory
# This preserves the actual satellite path (both lat and lon changes)
image_positions = []

# Always include the closest approach (time_rel ≈ 0)
closest_idx = (df['time_rel'].abs()).argmin()
sampled_indices = [closest_idx]

# Calculate spacing for other samples
if num_steps > 1:
    # Sample evenly across the trajectory, excluding the closest approach
    remaining_indices = [i for i in range(len(df)) if i != closest_idx]
    step_size = len(remaining_indices) / (num_steps - 1) if num_steps > 1 else 1
    for i in range(num_steps - 1):
        idx = remaining_indices[min(int(i * step_size), len(remaining_indices) - 1)]
        sampled_indices.append(idx)
    sampled_indices.sort()

for i, idx in enumerate(sampled_indices):
    row = df.iloc[idx]
    image_positions.append({
        'image_num': i + 1,
        'center_lat': row['lat'],
        'center_lon': row['lon'],
        'swath_km': swath_km,
        'time_rel': row['time_rel'],
        'altitude_km': row['alt']
    })

df_images = pd.DataFrame(image_positions)
    
    # Display results
    # print("=" * 80)
    # print("SATELLITE TRAJECTORY (60 seconds: -30s to +30s from closest approach)")
    # print("=" * 80)
    # print()
    # print(df[['time_rel', 'lat', 'lon', 'alt', 'dist_to_delft']].to_string(
    #     formatters={
    #         'time_rel': lambda x: f'{x:7.1f}s',
    #         'lat': lambda x: f'{x:8.4f}°',
    #         'lon': lambda x: f'{x:8.4f}°',
    #         'alt': lambda x: f'{x:7.2f}km',
    #         'dist_to_delft': lambda x: f'{x:7.4f}km'
    #     }
    # ))
    # print()
    # print("=" * 80)
    # print("IMAGE COVERAGE POSITIONS (8km x 8km swaths)")
    # print("=" * 80)
    # print()
    # print(df_images[['image_num', 'center_lat', 'center_lon', 'time_rel', 'altitude_km', 'swath_km']].to_string(
    #     formatters={
    #         'center_lat': lambda x: f'{x:.4f}°N',
    #         'center_lon': lambda x: f'{x:.4f}°E',
    #         'time_rel': lambda x: f'{x:7.1f}s',
    #         'altitude_km': lambda x: f'{x:7.2f}km',
    #         'swath_km': lambda x: f'{x}km'
    #     },
    #     index=False
    # ))
    # print()
print(f"Total coverage area: {num_steps} images × {swath_km}km = {num_steps * swath_km}km N-S extent")
    # print()