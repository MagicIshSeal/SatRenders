import cv2
import numpy as np
from PIL import Image
import math
from orbit import df_images, df, haversine

def create_flyby_video(stitched_image_path, output_video_path, speed_kmh=None, speed_ms=None, 
                       fps=30, viewport_width_pixels=None):
    """
    Create a video simulating the satellite flyby over the stitched image.
    Pans from bottom to top following the diagonal trajectory line.
    
    Args:
        stitched_image_path: Path to the stitched satellite image
        output_video_path: Output video file path
        speed_kmh: Speed in km/h (alternatively use speed_ms)
        speed_ms: Speed in m/s (alternatively use speed_kmh)
        fps: Frames per second for the video
        viewport_width_pixels: Width of the viewport in pixels (default: 800 pixels = 8km)
    
    The video pans from bottom to top, staying centered on the trajectory.
    """
    
    if speed_kmh is None and speed_ms is None:
        raise ValueError("Must specify either speed_kmh or speed_ms")
    
    if speed_kmh is not None:
        speed_ms = speed_kmh * 1000 / 3600  # Convert km/h to m/s
    
    # Load the stitched image
    img = Image.open(stitched_image_path)
    img_array = np.array(img)
    img_height, img_width = img_array.shape[:2]
    
    # Default viewport width is 8km (same as one image swath)
    if viewport_width_pixels is None:
        viewport_width_pixels = 800  # 8km at 10m/pixel resolution
    
    viewport_height = viewport_width_pixels  # Square viewport
    
    # Get the center positions of first and last images
    first_image = df_images.iloc[0]
    last_image = df_images.iloc[-1]
    
    first_lat, first_lon = first_image['center_lat'], first_image['center_lon']
    last_lat, last_lon = last_image['center_lat'], last_image['center_lon']
    
    # Reference point for coordinate conversion
    ref_lat = first_lat
    ref_lon = first_lon
    
    # Convert lat/lon to pixel positions
    def latlon_to_pixels(lat, lon, ref_lat, ref_lon):
        dlat = lat - ref_lat
        dlon = lon - ref_lon
        
        dlat_m = dlat * 111000
        dlon_m = -dlon * 111000 * math.cos(math.radians(ref_lat))
        
        pixels_per_meter = 1 / 10.0
        px = int(dlat_m * pixels_per_meter)
        py = int(dlon_m * pixels_per_meter)
        
        return px, py
    
    # Get pixel positions of first and last image centers
    first_px, first_py = latlon_to_pixels(first_lat, first_lon, ref_lat, ref_lon)
    last_px, last_py = latlon_to_pixels(last_lat, last_lon, ref_lat, ref_lon)
    
    # Pre-compute pixel positions for all image centers
    image_centers_px = []
    for idx, row in df_images.iterrows():
        px, py = latlon_to_pixels(row['center_lat'], row['center_lon'], ref_lat, ref_lon)
        image_centers_px.append((px, py))
    
    print(f"First image center: ({first_px}, {first_py}) pixels")
    print(f"Last image center: ({last_px}, {last_py}) pixels")
    
    # Calculate total distance along the trajectory
    total_distance_m = 0
    for i in range(1, len(df)):
        dist = haversine(
            df.iloc[i-1]['lat'], df.iloc[i-1]['lon'],
            df.iloc[i]['lat'], df.iloc[i]['lon']
        ) * 1000  # Convert km to m
        total_distance_m += dist
    
    # Calculate video duration and frame count
    duration_s = total_distance_m / speed_ms
    num_frames = int(duration_s * fps)
    
    print(f"Creating video:")
    print(f"  Image size: {img_width} x {img_height} pixels")
    print(f"  Viewport: {viewport_width_pixels} x {viewport_height} pixels")
    print(f"  Speed: {speed_ms:.1f} m/s ({speed_ms * 3.6:.1f} km/h)")
    print(f"  Total distance: {total_distance_m/1000:.2f} km")
    print(f"  Duration: {duration_s:.1f} seconds")
    print(f"  Frames: {num_frames}")
    
    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (viewport_width_pixels, viewport_height))
    
    # Create video frames
    for frame_num in range(num_frames):
        # Calculate current position along the trajectory (1 to 0 for bottom-to-top)
        progress = 1.0 - (frame_num / max(1, num_frames - 1) if num_frames > 1 else 0)
        
        # Interpolate position along the diagonal line
        current_px = first_px + (last_px - first_px) * progress
        current_py = first_py + (last_py - first_py) * progress
        
        # Determine which image center to look towards
        # Calculate which image we're closest to in the timeline
        progress_from_start = 1.0 - progress
        image_index = min(int(progress_from_start * (len(image_centers_px) - 1) + 0.5), len(image_centers_px) - 1)
        
        # Use the next image center if available, otherwise use current
        next_image_index = min(image_index + 1, len(image_centers_px) - 1)
        target_px, target_py = image_centers_px[next_image_index]
        
        # Calculate direction from current position to target image center
        dx = target_px - current_px
        dy = target_py - current_py
        distance = math.sqrt(dx**2 + dy**2)
        
        # Normalize and scale to viewport offset (400 pixels)
        offset_distance = 400
        if distance > 0:
            offset_px = int((dx / distance) * offset_distance)
            offset_py = int((dy / distance) * offset_distance)
        else:
            offset_px = 0
            offset_py = 400  # Default to right if at same position
        
        # Define the center of the viewport
        center_x = int(current_px)
        center_y = int(current_py)
        
        # Calculate the top-left corner of the viewport with dynamic offset based on direction
        x_start = center_x - viewport_height // 2 + offset_px
        y_start = center_y - viewport_width_pixels // 2 + offset_py
        
        # Extract viewport from image with bounds checking
        viewport = np.zeros((viewport_height, viewport_width_pixels, img_array.shape[2]), dtype=np.uint8)
        
        for dy in range(viewport_height):
            for dx in range(viewport_width_pixels):
                img_y = x_start + dy
                img_x = y_start + dx
                
                if 0 <= img_y < img_height and 0 <= img_x < img_width:
                    viewport[dy, dx] = img_array[img_y, img_x]
        
        # Convert RGB to BGR for OpenCV
        viewport_bgr = cv2.cvtColor(viewport.astype(np.uint8), cv2.COLOR_RGB2BGR)
        
        # Write frame
        out.write(viewport_bgr)
        
        if (frame_num + 1) % max(1, num_frames // 10) == 0:
            print(f"  Frame {frame_num + 1}/{num_frames}")
    
    out.release()
    print(f"Video saved: {output_video_path}")


if __name__ == "__main__":
    # Example usage
    try:
        # Create a flyby video at realistic satellite speed
        create_flyby_video(
            stitched_image_path="img/stitched.png",
            output_video_path="img/flyby_video.mp4",
            speed_kmh=25200,  # ~7.5 km/s converted to km/h
            fps=15,
            viewport_width_pixels=800  # 8km viewport
        )
    except Exception as e:
        print(f"Error creating video: {e}")
        import traceback
        traceback.print_exc()