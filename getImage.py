import math
import openeo
from orbit import df_images
import time
def getImage(lat, lon, swath_km, num = 1):
    half_lat = (swath_km / 2) / 111.0
    half_lon = (swath_km / 2) / (111.0 * math.cos(math.radians(lat)))

    bbox = {
        "west":  lon - half_lon,
        "east":  lon + half_lon,
        "south": lat - half_lat,
        "north": lat + half_lat,
        "crs":   "EPSG:4326",
    }

    con = openeo.connect("openeo.dataspace.copernicus.eu")
    con.authenticate_oidc()

    cube = con.load_collection(
        "SENTINEL2_L2A",
        spatial_extent=bbox,
        temporal_extent=["2026-04-28", "2026-04-30"],
        bands=["B04", "B03", "B02"],
    )

    cube = cube.min_time()
    #cube = cube.resample_spatial(resolution=10, projection="EPSG:32631")
    cube = cube.linear_scale_range(0, 4000, 0, 255)
    try:
        #cube.download(f"img/snapshot_{num}.png", format="PNG")
        job = cube.create_job(format="PNG", title=f"snapshot_{num}")
        print(f"Image {num} downloaded successfully.")
        return job
    except Exception as e:
        print(f"Error downloading image {num}: {e}")
        return None


if __name__ == "__main__":
    j = 0
    for i in df_images["image_num"]:
        t1 = time.time()
        row = df_images[df_images["image_num"] == i].iloc[0]
        job = getImage(row["center_lat"], row["center_lon"], 12, num=i)
        j = j + 1
        if j > 1:
            job.start_job()
        print(f"Time taken for image {i}: {time.time() - t1:.2f} seconds")
    # lat = 51.9968
    # lon = 4.3187
    # lat2 = 52.0588
    # lon2 = 4.2927
    # swath_km = 8
    # step_lat = swath_km / 111.0
    # getImage(lat, lon, swath_km, num=1)
    # getImage(lat2, lon2, swath_km, num=2)