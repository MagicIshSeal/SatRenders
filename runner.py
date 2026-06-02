from getImage import getImage
from orbit import df_images
from stitchImage import stitch_images
from createVideo import create_flyby_video
import os
import time

if __name__ == "__main__":
    try:
        for i in df_images["image_num"]:
            t1 = time.time()
            row = df_images[df_images["image_num"] == i].iloc[0]
            getImage(row["center_lat"], row["center_lon"], row["swath_km"], num=i)
            print(f"Time taken for image {i}: {time.time() - t1:.2f} seconds")
        print("\nAll images downloaded. Starting stitching process...")
        
        image_nums = sorted(df_images['image_num'].tolist())
        
        # Build list of image files
        image_files = [f"img/snapshot_{int(num)}.png" for num in image_nums]
        
        # Check if all images exist
        missing_files = [f for f in image_files if not os.path.exists(f)]
        if missing_files:
            print(f"Warning: Missing files: {missing_files}")
        
        # Build coordinates list from df_images, maintaining the order
        coordinates = []
        for num in image_nums:
            row = df_images[df_images['image_num'] == num].iloc[0]
            coordinates.append({
                'center_lat': row['center_lat'],
                'center_lon': row['center_lon'],
                'altitude_km': row['altitude_km']
            })
        # Stitch the images
        stitched = stitch_images(image_files, coordinates)
        stitched.save("img/stitched.png")
        
        print("\nStitching completed. Starting video creation...")
        create_flyby_video(
            stitched_image_path="img/stitched.png",
            output_video_path="img/flyby_video.mp4",
            speed_kmh=25200,  # ~7.5 km/s converted to km/h
            fps=60,
            viewport_width_pixels=800  # 8km viewport
        )
    except Exception as e:
        print(f"Error occurred: {e}")
        quit()

        
    