from getImage import getImage
from orbit import getdfImages
from stitchImage import runStitch
from createVideo import create_flyby_video
import argparse
import time
import os

DEFAULT_LAT, DEFAULT_LON = 51.9973, 4.368927  # Default target location (can be overridden by user input)
DEFAULT_SWATH_KM = 12
DEFAULT_SPEED_KMS = 7.5*1000 #km/s
DEFAULT_FPS = 60
DEFAULT_VIEWPORT_WIDTH = 1920
DEFAULT_VIEWPORT_HEIGHT = 1080
DEFAULT_INC = 97.88

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Satellite render pipeline")
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT, help="Target latitude")
    parser.add_argument("--lon", type=float, default=DEFAULT_LON, help="Target longitude")
    parser.add_argument("--inc", type=float, default=DEFAULT_INC, help="Satellite inclination in degrees")
    parser.add_argument("--swath-km", type=float, default=DEFAULT_SWATH_KM, help="Swath width in km")
    parser.add_argument("--lead-km", type=float, default=20, help="Lead distance in km")
    parser.add_argument("--trail-km", type=float, default=10, help="Trail distance in km")
    parser.add_argument("--speed-ms", type=float, default=DEFAULT_SPEED_KMS, help="Speed in km/s")
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS, help="Video FPS")
    parser.add_argument("--width", type=int, default=DEFAULT_VIEWPORT_WIDTH, help="Viewport width")
    parser.add_argument("--height", type=int, default=DEFAULT_VIEWPORT_HEIGHT, help="Viewport height")
    parser.add_argument("--output", type=str, default="img/flyby_video.mp4", help="Output video path")
    args = parser.parse_args()
    
    try:
        df_images = getdfImages(args.lat, args.lon, args.inc, km_lead=args.lead_km, km_trail=args.trail_km, swath_km=args.swath_km)

        for i in df_images["image_num"]:
            t1 = time.time()
            row = df_images[df_images["image_num"] == i].iloc[0]
            getImage(row["center_lat"], row["center_lon"], row["swath_km"], num=i)
            print(f"\nTime taken for image {i}: {time.time() - t1:.2f} seconds")
        print("\nAll images downloaded successfully.")
        
        runStitch(df_images)
        
        create_flyby_video(df_images,
            stitched_image_path="img/stitched.png",
            output_video_path=args.output,
            speed_ms=args.speed_ms,
            fps=args.fps,
            viewport_width=args.width,
            viewport_height=args.height
        )   
    except Exception as e:
        print(f"Error occurred: {e}")
        quit()

        
    