from PIL import Image
import numpy as np

def stitch_images(image_files, coordinates):
    """
    Stitch satellite images accounting for non-vertical trajectory.
    
    Args:
        image_files: List of image file paths
        coordinates: List of dicts with 'center_lat', 'center_lon', 'altitude_km' for each image
    """
    if not image_files or not coordinates:
        raise ValueError("Must provide image files and coordinates")
    
    if len(image_files) != len(coordinates):
        raise ValueError("Number of images must match number of coordinates")
    
    # Open all images
    images = [Image.open(f) for f in image_files]
    img_width, img_height = images[0].size
    
    # Convert lat/lon coordinates to pixel offsets
    # Use first image as reference (0, 0)
    ref_lat = coordinates[0]['center_lat']
    ref_lon = coordinates[0]['center_lon']
    
    # Pixel size calculation (10m resolution from orbit.py)
    pixels_per_meter = 1 / 10.0  # 10m per pixel
    
    # Get the swath size (10km = 10000m)
    swath_m = 8000
    swath_pixels = int(swath_m * pixels_per_meter)  # Should be 1000 pixels
    
    # Calculate pixel positions for each image center
    positions = []
    for i, coord in enumerate(coordinates):
        lat = coord['center_lat']
        lon = coord['center_lon']
        
        # Calculate displacement from reference in degrees
        dlat = lat - ref_lat
        dlon = lon - ref_lon
        
        # Convert degrees to meters
        # 1 degree latitude ≈ 111 km
        dlat_m = dlat * 111000
        
        # 1 degree longitude ≈ 111 * cos(lat) km
        dlon_m = dlon  *55000
        
        
        # Convert meters to pixels (10m resolution)
        # Negate px_offset to stitch to the opposite side
        px_offset = -int(dlat_m * pixels_per_meter)
        py_offset = int(dlon_m * pixels_per_meter)
        
        positions.append((px_offset, py_offset))
    
    # Calculate canvas size to fit all images
    min_x = min(p[0] for p in positions)
    max_x = max(p[0] for p in positions) + img_height
    min_y = min(p[1] for p in positions)
    max_y = max(p[1] for p in positions) + img_width
    
    canvas_height = max_x - min_x
    canvas_width = max_y - min_y
    
    # Create canvas (add some padding)
    padding = 0
    canvas = Image.new("RGB", (canvas_width + 2*padding, canvas_height + 2*padding), color=(0, 0, 0))
    
    # Paste each image at its calculated position
    for i, img in enumerate(images):
        # Adjust position to account for canvas origin and padding
        x = positions[i][0] - min_x + padding
        y = positions[i][1] - min_y + padding
        canvas.paste(img, (y, x))  # PIL uses (x, y) where x is column, y is row
    
    return canvas

def runStitch(df_images):
    # Get image numbers from df_images
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
                'center_lon': row['center_lon']
            })
        
        print(f"Found {len(image_files)} images to stitch")
        print(f"Image files: {image_files}")
        print(f"Coordinates:")
        for i, coord in enumerate(coordinates):
            print(f"  Image {i+1}: Lat {coord['center_lat']:.4f}°N, Lon {coord['center_lon']:.4f}°E")
        
        # Stitch the images
        stitched = stitch_images(image_files, coordinates)
        stitched.save("img/stitched.png")
        print(f"\nStitched image saved: img/stitched.png")
        print(f"Canvas size: {stitched.size}")

if __name__ == "__main__":
    import os
    from orbit import df_images
    
    try:
        # Get image numbers from df_images
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
                'center_lon': row['center_lon']
            })
        
        print(f"Found {len(image_files)} images to stitch")
        print(f"Image files: {image_files}")
        print(f"Coordinates:")
        for i, coord in enumerate(coordinates):
            print(f"  Image {i+1}: Lat {coord['center_lat']:.4f}°N, Lon {coord['center_lon']:.4f}°E")
        
        # Stitch the images
        stitched = stitch_images(image_files, coordinates)
        stitched.save("img/stitched.png")
        print(f"\nStitched image saved: img/stitched.png")
        print(f"Canvas size: {stitched.size}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()