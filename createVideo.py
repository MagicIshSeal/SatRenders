import cv2
import numpy as np
from PIL import Image
import math

def toPx(lat, lon, img_width, img_height, ref_lat=None, ref_lon=None, min_x=None, min_y=None, padding=0):
    """
    Convert lat/lon to pixel coordinates in the stitched image.
    Uses the same coordinate system as stitch_images.
    """
    if ref_lat is None:
        ref_lat = df_images.iloc[0]['center_lat']
    if ref_lon is None:
        ref_lon = df_images.iloc[0]['center_lon']
    
    # Calculate displacement from reference in degrees
    dlat = lat - ref_lat
    dlon = lon - ref_lon
    
    # Convert degrees to meters
    # 1 degree latitude ≈ 111 km
    dlat_m = dlat * 111000
    
    # 1 degree longitude ≈ 111 * cos(lat) km (using ~55km for approximation at typical latitude)
    dlon_m = dlon * 55000
    
    # Pixel size calculation (10m resolution)
    pixels_per_meter = 1 / 10.0
    
    # Convert meters to pixels
    px_offset = -int(dlat_m * pixels_per_meter)
    py_offset = int(dlon_m * pixels_per_meter)
    
    # If min_x and min_y are provided, adjust for canvas offset (from stitching)
    if min_x is not None:
        px_offset = px_offset - min_x + padding
    if min_y is not None:
        py_offset = py_offset - min_y + padding
    
    return py_offset, px_offset

def create_flyby_video(stitched_image_path, output_video_path, speed_kmh=None, speed_ms=None, 
                       fps=30, viewport_width=800, viewport_height=600):

    if speed_kmh is None and speed_ms is None:
        raise ValueError("Must specify either speed_kmh or speed_ms")
    
    if speed_kmh is not None:
        speed_ms = speed_kmh * 1000 / 3600  # Convert km/h to m/s
    
    # Load the stitched image
    img = Image.open(stitched_image_path)
    img_array = np.array(img)
    img_height, img_width = img_array.shape[:2]
    
    # Calculate canvas offsets (same as in stitchImage.py)
    # Get reference position (first image)
    ref_lat = df_images.iloc[0]['center_lat']
    ref_lon = df_images.iloc[0]['center_lon']
    
    # Pixel size calculation (10m resolution)
    pixels_per_meter = 1 / 10.0
    img_size = 512  # Assuming square images
    
    # Calculate positions for all images to get min_x, min_y
    positions = []
    for idx, row in df_images.iterrows():
        lat = row['center_lat']
        lon = row['center_lon']
        
        dlat = lat - ref_lat
        dlon = lon - ref_lon
        
        dlat_m = dlat * 111000
        dlon_m = dlon * 55000
        
        px_offset = -int(dlat_m * pixels_per_meter)
        py_offset = int(dlon_m * pixels_per_meter)
        
        positions.append((px_offset, py_offset))
    
    min_x = min(p[0] for p in positions)
    min_y = min(p[1] for p in positions)
    
    # Get the center positions of first and last images
    first_image = df_images.iloc[0]
    last_image = df_images.iloc[-1]
    
    out = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (viewport_width, viewport_height))
    
    first_lat, first_lon = first_image['center_lat'], first_image['center_lon']
    last_lat, last_lon = last_image['center_lat'], last_image['center_lon']
    
    first_x, first_y = toPx(first_lat, first_lon, img_width, img_height, ref_lat, ref_lon, min_x, min_y)
    last_x, last_y = toPx(last_lat, last_lon, img_width, img_height, ref_lat, ref_lon, min_x, min_y)
    
    # Add image size offset to get the actual center (toPx returns top-left corner)
    first_x += img_size // 2
    first_y += img_size // 2
    last_x += img_size // 2
    last_y += img_size // 2
    distance_px = math.sqrt((last_x - first_x) ** 2 + (last_y - first_y) ** 2)
    distance_m = distance_px * 10  # Assuming 1 pixel = 10 meters for simplicity
    total_time_s = distance_m / speed_ms
    total_frames = int(total_time_s * fps)
    
    for frame in range(total_frames):
        t = frame / total_frames
        current_x = int(first_x + t * (last_x - first_x))
        current_y = int(first_y + t * (last_y - first_y))
        
        # Extract viewport region centered at current position
        # Define desired viewport bounds (offset to the right by half viewport width)
        vp_left = current_x
        vp_top = current_y - viewport_height // 2
        vp_right = vp_left + viewport_width
        vp_bottom = vp_top + viewport_height
        
        # Clip to image bounds
        src_left = max(0, vp_left)
        src_top = max(0, vp_top)
        src_right = min(img_width, vp_right)
        src_bottom = min(img_height, vp_bottom)
        
        # Calculate where to place the extracted region in the viewport
        dst_left = src_left - vp_left
        dst_top = src_top - vp_top
        dst_right = dst_left + (src_right - src_left)
        dst_bottom = dst_top + (src_bottom - src_top)
        
        # Handle boundary cases - pad with black if needed
        viewport = np.zeros((viewport_height, viewport_width, 3), dtype=np.uint8)
        
        # Copy the extracted region (handle all 3 channels)
        viewport[dst_top:dst_bottom, dst_left:dst_right, :] = img_array[src_top:src_bottom, src_left:src_right, :]
        
        viewport_bgr = cv2.cvtColor(viewport.astype(np.uint8), cv2.COLOR_RGB2BGR)
        out.write(viewport_bgr)
        print(f"Frame {frame+1}/{total_frames} - Position: ({current_x}, {current_y})")
    
    out.release()
    print(f"Video saved: {output_video_path}")


if __name__ == "__main__":
    # Example usage
    try:
        # Create a simple flyby video with straight-line motion
        create_flyby_video(
            stitched_image_path="img/stitched.png",
            output_video_path="img/flyby_video.mp4",
            speed_ms=7.5*1000,  # ~7.5 km/s converted to km/h
            fps=60,
            viewport_width=1920,   # Width in pixels
            viewport_height=1080    # Height in pixels
            #9:16 aspect ratio for vertical video (e.g., 1080x1920)
        )
    except Exception as e:
        print(f"Error creating video: {e}")
        import traceback
        traceback.print_exc()